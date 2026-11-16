"""Persist pipeline results and enforce revision-aware human review."""

from collections import Counter
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from threading import Lock
from typing import Literal

from sqlalchemy import select, update
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session, sessionmaker

from hiring_inbox.classifier import Intent
from hiring_inbox.csv_io import ImportedMessage, export_csv, fingerprint, has_unsupported_controls
from hiring_inbox.database import Batch, Draft, Message, ReviewEvent
from hiring_inbox.draft_safety import draft_safety_flags
from hiring_inbox.pipeline import PipelineResult, process_message
from hiring_inbox.provider import StructuredProvider
from hiring_inbox.schemas import ReviewDraft


_MANUAL_OUTCOMES = {
    "unsafe_draft", "manual_writing_requested", "skipped_after_candidate_instruction",
}


class ServiceError(Exception):
    def __init__(self, status: int, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail


def recover_interrupted_work(sessions: sessionmaker[Session]) -> None:
    with sessions.begin() as session:
        session.execute(update(Batch).where(Batch.status == "processing").values(status="interrupted"))
        session.execute(update(Draft).where(Draft.regenerating.is_(True)).values(
            regenerating=False,
            generation_failure="regeneration_interrupted",
            review_reason="Regeneration was interrupted. Write a reply or regenerate again.",
        ))


def _effective_flags(draft: Draft) -> list[str]:
    flags = list(draft_safety_flags(draft.reply)) if draft.reply else []
    if draft.reply and has_unsupported_controls(draft.reply):
        flags.append("control_characters")
    if draft.edited_reply is None:
        flags.extend(draft.generation_safety_flags)
    return list(dict.fromkeys(flags))


def _requires_manual_writing(draft: Draft) -> bool:
    return not (draft.reply and draft.reply.strip()) or bool(_effective_flags(draft))


def _processing_failed(message: Message, draft: Draft) -> bool:
    return bool(message.classification_failure or (
        draft.generation_failure and draft.generation_failure not in _MANUAL_OUTCOMES
    ))


def _run_pipeline(provider: StructuredProvider, text: str) -> PipelineResult:
    try:
        return process_message(provider, text)
    except Exception:
        # Keep unexpected provider failures isolated to this message and omit exception text.
        return PipelineResult(
            classification=None,
            draft=ReviewDraft(None, "Processing failed. Write a reply or regenerate."),
            classification_failure="processing_error",
            draft_failure="skipped_after_classification_failure",
        )


def _store_generation(message: Message, draft: Draft, result: PipelineResult) -> None:
    classification = result.classification
    message.primary_intent = classification.primary_intent.value if classification else None
    message.classification = classification.model_dump(mode="json") if classification else None
    message.classification_failure = result.classification_failure
    message.candidate_instruction_detected = result.candidate_instruction_detected
    draft.generated_reply = result.draft.draft_reply
    draft.review_reason = result.draft.review_reason
    draft.generation_failure = result.draft_failure
    draft.generation_safety_flags = list(result.safety_flags)


def _batch(session: Session, batch_id: int) -> Batch:
    batch = session.get(Batch, batch_id)
    if batch is None:
        raise ServiceError(404, "Batch not found.")
    return batch


def _draft(session: Session, draft_id: int) -> Draft:
    draft = session.get(Draft, draft_id)
    if draft is None:
        raise ServiceError(404, "Draft not found.")
    return draft


def _check_review_revision(draft: Draft, revision: int) -> None:
    if draft.revision != revision:
        raise ServiceError(409, "Draft revision changed. Reload it before reviewing.")
    if draft.regenerating:
        raise ServiceError(409, "Draft regeneration is in progress.")


def _transition(
    session: Session, draft: Draft, action: str, reason: str | None, changes: dict, reply_after: str | None,
) -> ReviewEvent:
    updated = session.execute(
        update(Draft).where(
            Draft.id == draft.id, Draft.revision == draft.revision, Draft.status == draft.status,
            Draft.regenerating.is_(False),
        ).values(**changes).execution_options(synchronize_session=False)
    )
    if updated.rowcount != 1:
        raise ServiceError(409, "Draft changed. Reload it before reviewing.")
    event = ReviewEvent(
        draft_id=draft.id, action=action, from_revision=draft.revision,
        to_revision=changes.get("revision", draft.revision), from_status=draft.status,
        to_status=changes["status"], reply_before=draft.reply, reply_after=reply_after, reason=reason,
        safety_flags_before=_effective_flags(draft), generation_failure_before=draft.generation_failure,
    )
    session.add(event)
    session.refresh(draft)
    return event


def _draft_summary(draft: Draft) -> dict:
    return {
        "id": draft.id,
        "status": draft.status,
        "revision": draft.revision,
        "approved_revision": draft.approved_revision,
        "regenerating": draft.regenerating,
        "requires_manual_writing": _requires_manual_writing(draft),
    }


def _draft_detail(session: Session, draft: Draft) -> dict:
    events = session.scalars(
        select(ReviewEvent).where(ReviewEvent.draft_id == draft.id).order_by(ReviewEvent.id)
    ).all()
    return {
        **_draft_summary(draft),
        "message_id": draft.message_id,
        "generated_reply": draft.generated_reply,
        "edited_reply": draft.edited_reply,
        "reply": draft.reply,
        "review_reason": draft.review_reason,
        "generation_failure": draft.generation_failure,
        "generation_safety_flags": draft.generation_safety_flags,
        "safety_flags": _effective_flags(draft),
        "review_events": events,
    }


class ReviewService:
    def __init__(
        self, sessions: sessionmaker[Session],
        provider: Callable[[], AbstractContextManager[StructuredProvider]],
    ) -> None:
        self.sessions = sessions
        self.provider = provider
        self.generation_lock = Lock()

    @contextmanager
    def _generation_slot(self) -> Iterator[None]:
        if not self.generation_lock.acquire(blocking=False):
            raise ServiceError(409, "Another processing or regeneration request is active.")
        try:
            yield
        finally:
            self.generation_lock.release()

    def import_batch(self, messages: list[ImportedMessage]) -> dict:
        digest = fingerprint(messages)
        with self.sessions.begin() as session:
            inserted = session.execute(
                insert(Batch).values(fingerprint=digest).on_conflict_do_nothing(index_elements=[Batch.fingerprint])
            )
            batch_id = session.scalar(select(Batch.id).where(Batch.fingerprint == digest))
            duplicate = inserted.rowcount == 0
            if not duplicate:
                session.add_all(Message(
                    batch_id=batch_id, source_id=row.source_id,
                    candidate_name=row.candidate_name, message_text=row.message_text,
                ) for row in messages)
        return {"batch_id": batch_id, "message_count": len(messages), "duplicate": duplicate}

    def _set_batch_status(self, batch_id: int, status: str) -> None:
        with self.sessions.begin() as session:
            _batch(session, batch_id).status = status

    def process_batch(self, batch_id: int) -> dict:
        with self._generation_slot():
            with self.sessions() as session:
                batch = _batch(session, batch_id)
                if batch.status == "completed":
                    return self.status(batch_id)
                pending = session.execute(
                    select(Message.id, Message.message_text).outerjoin(Draft, Draft.message_id == Message.id)
                    .where(Message.batch_id == batch_id, Draft.id.is_(None)).order_by(Message.id)
                ).all()
            if pending:
                with self.provider() as provider:
                    self._set_batch_status(batch_id, "processing")
                    try:
                        for message_id, text in pending:
                            result = _run_pipeline(provider, text)
                            with self.sessions.begin() as session:
                                message = session.get(Message, message_id)
                                draft = Draft(message_id=message_id)
                                _store_generation(message, draft, result)
                                session.add(draft)
                    except Exception:
                        self._set_batch_status(batch_id, "interrupted")
                        raise
            self._set_batch_status(batch_id, "completed")
        return self.status(batch_id)

    def _batch_rows(self, batch_id: int) -> list:
        with self.sessions() as session:
            rows = session.execute(
                select(Batch, Message, Draft).join(Message, Message.batch_id == Batch.id)
                .outerjoin(Draft, Draft.message_id == Message.id).where(Batch.id == batch_id).order_by(Message.id)
            ).all()
        if not rows:
            raise ServiceError(404, "Batch not found.")
        return rows

    def status(self, batch_id: int) -> dict:
        rows = self._batch_rows(batch_id)
        batch = rows[0][0]
        processed = [(message, draft) for _, message, draft in rows if draft is not None]
        counts = Counter(draft.status for _, draft in processed)
        failures = sum(_processing_failed(message, draft) for message, draft in processed)
        status = "completed_with_errors" if batch.status == "completed" and failures else batch.status
        return {
            "batch_id": batch_id, "status": status, "created_at": batch.created_at,
            "message_count": len(rows), "processed": len(processed), "processing_failures": failures,
            "classified": sum(message.primary_intent is not None for _, message, _ in rows),
            "pending_review": counts["pending_review"], "approved": counts["approved"],
            "rejected": counts["rejected"],
            "manual_writing": sum(_requires_manual_writing(draft) for _, draft in processed),
            "regenerating": sum(draft.regenerating for _, draft in processed),
        }

    def groups(self, batch_id: int) -> dict:
        groups = {intent.value: [] for intent in Intent} | {"unclassified": []}
        for _, message, draft in self._batch_rows(batch_id):
            groups[message.primary_intent or "unclassified"].append({
                "id": message.id, "source_id": message.source_id, "candidate_name": message.candidate_name,
                "message_text": message.message_text, "classification": message.classification,
                "classification_failure": message.classification_failure,
                "candidate_instruction_detected": message.candidate_instruction_detected,
                "draft": _draft_summary(draft) if draft else None,
            })
        return {"batch_id": batch_id, "groups": [
            {"intent": intent, "messages": messages} for intent, messages in groups.items() if messages
        ]}

    def get_draft(self, draft_id: int) -> dict:
        with self.sessions() as session:
            return _draft_detail(session, _draft(session, draft_id))

    def review(
        self, draft_id: int, revision: int, action: Literal["edit", "approve", "reject"],
        reason: str | None, reply: str | None = None,
    ) -> dict:
        with self.sessions.begin() as session:
            draft = _draft(session, draft_id)
            _check_review_revision(draft, revision)
            if action == "approve":
                if draft.status != "pending_review" or _requires_manual_writing(draft):
                    raise ServiceError(409, "Only a safe, non-empty pending draft can be approved.")
                changes = {"status": "approved", "approved_revision": revision}
            elif action == "reject":
                if draft.status == "rejected":
                    raise ServiceError(409, "Draft is already rejected.")
                changes = {"status": "rejected", "approved_revision": None}
            else:  # The PATCH route supplies a validated replacement reply.
                changes = {"status": "pending_review", "approved_revision": None,
                           "revision": revision + 1, "edited_reply": reply}
            _transition(session, draft, action, reason, changes, reply if action == "edit" else draft.reply)
            return _draft_detail(session, draft)

    def regenerate(self, draft_id: int, revision: int, reason: str | None) -> dict:
        with self._generation_slot():
            with self.sessions() as session:
                _check_review_revision(_draft(session, draft_id), revision)
            with self.provider() as provider:
                with self.sessions.begin() as session:
                    draft = _draft(session, draft_id)
                    _check_review_revision(draft, revision)
                    event = _transition(session, draft, "regenerate", reason, {
                        "status": "pending_review", "revision": revision + 1, "approved_revision": None,
                        "edited_reply": None, "generated_reply": None, "regenerating": True,
                        "review_reason": "Regeneration in progress.", "generation_failure": None,
                        "generation_safety_flags": [],
                    }, None)
                    message_text = session.get(Message, draft.message_id).message_text
                result = _run_pipeline(provider, message_text)
                with self.sessions.begin() as session:
                    draft = _draft(session, draft_id)
                    _store_generation(session.get(Message, draft.message_id), draft, result)
                    draft.regenerating = False
                    session.get(ReviewEvent, event.id).reply_after = draft.reply
                    return _draft_detail(session, draft)

    def export(self, batch_id: int) -> str:
        with self.sessions() as session:
            _batch(session, batch_id)
            approved = session.execute(
                select(Message, Draft).join(Draft, Draft.message_id == Message.id).where(
                    Message.batch_id == batch_id, Draft.status == "approved",
                    Draft.approved_revision == Draft.revision, Draft.regenerating.is_(False),
                ).order_by(Message.id)
            ).all()
            return export_csv([
                (message.source_id, message.candidate_name, message.primary_intent or "unclassified",
                 draft.id, draft.revision, draft.reply)
                for message, draft in approved if not _requires_manual_writing(draft)
            ])

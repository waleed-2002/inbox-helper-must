"""SQLite storage for imports, processing results, and review history."""

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import JSON, CheckConstraint, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy import URL, create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_timestamp() -> str:
    return datetime.now(UTC).isoformat()


class Base(DeclarativeBase):
    pass


class Batch(Base):
    __tablename__ = "batches"
    __table_args__ = (
        CheckConstraint("status IN ('imported', 'processing', 'interrupted', 'completed')"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True)
    status: Mapped[str] = mapped_column(String(16), default="imported")
    created_at: Mapped[str] = mapped_column(default=utc_timestamp)


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (UniqueConstraint("batch_id", "source_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("batches.id"))
    source_id: Mapped[str] = mapped_column(String(64))
    candidate_name: Mapped[str] = mapped_column(String(200))
    message_text: Mapped[str] = mapped_column(Text)
    primary_intent: Mapped[str | None] = mapped_column(String(32))
    classification: Mapped[dict | None] = mapped_column(JSON)
    classification_failure: Mapped[str | None]
    candidate_instruction_detected: Mapped[bool] = mapped_column(default=False)


class Draft(Base):
    __tablename__ = "drafts"
    __table_args__ = (
        CheckConstraint("revision >= 1"),
        CheckConstraint(
            "(status = 'approved' AND approved_revision IS NOT NULL AND approved_revision = revision "
            "AND NOT regenerating AND COALESCE(edited_reply, generated_reply) IS NOT NULL) OR "
            "(status IN ('pending_review', 'rejected') AND approved_revision IS NULL)"
        ),
        CheckConstraint("NOT regenerating OR status = 'pending_review'"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[int] = mapped_column(ForeignKey("messages.id"), unique=True)
    revision: Mapped[int] = mapped_column(default=1)
    status: Mapped[str] = mapped_column(String(16), default="pending_review")
    approved_revision: Mapped[int | None]
    generated_reply: Mapped[str | None] = mapped_column(Text)
    edited_reply: Mapped[str | None] = mapped_column(Text)
    review_reason: Mapped[str] = mapped_column(Text)
    generation_failure: Mapped[str | None]
    generation_safety_flags: Mapped[list[str]] = mapped_column(JSON)
    regenerating: Mapped[bool] = mapped_column(default=False)

    @property
    def reply(self) -> str | None:
        return self.edited_reply if self.edited_reply is not None else self.generated_reply


class ReviewEvent(Base):
    __tablename__ = "review_events"
    __table_args__ = (CheckConstraint("action IN ('edit', 'approve', 'reject', 'regenerate')"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    draft_id: Mapped[int] = mapped_column(ForeignKey("drafts.id"), index=True)
    action: Mapped[str] = mapped_column(String(16))
    from_revision: Mapped[int]
    to_revision: Mapped[int]
    from_status: Mapped[str]
    to_status: Mapped[str]
    reply_before: Mapped[str | None] = mapped_column(Text)
    reply_after: Mapped[str | None] = mapped_column(Text)
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(default=utc_timestamp)


def open_database(path: Path) -> Engine:
    path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(URL.create("sqlite+pysqlite", database=str(path)))

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record) -> None:
        cursor = connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys = ON")
        finally:
            cursor.close()

    Base.metadata.create_all(engine)
    return engine

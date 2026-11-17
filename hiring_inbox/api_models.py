"""Request and response models for the local HTTP API."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from hiring_inbox.classifier import Intent


DraftStatus = Literal["pending_review", "approved", "rejected"]


class ReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)

    revision: int = Field(gt=0, lt=2**63)
    reason: str | None = Field(default=None, min_length=1, max_length=500)


class EditRequest(ReviewRequest):
    reply: str = Field(min_length=1, max_length=1200)


class ImportReceipt(BaseModel):
    batch_id: int
    message_count: int
    duplicate: bool


class BatchSummary(BaseModel):
    batch_id: int
    created_at: str
    message_count: int


class BatchList(BaseModel):
    batches: list[BatchSummary]


class BatchStatus(BaseModel):
    batch_id: int
    status: Literal["imported", "processing", "interrupted", "completed", "completed_with_errors"]
    created_at: str
    message_count: int
    processed: int
    processing_failures: int
    classified: int
    pending_review: int
    approved: int
    rejected: int
    manual_writing: int
    regenerating: int


class DraftSummary(BaseModel):
    id: int
    status: DraftStatus
    revision: int
    approved_revision: int | None
    regenerating: bool
    requires_manual_writing: bool


class ReviewEventView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    action: Literal["edit", "approve", "reject", "regenerate"]
    from_revision: int
    to_revision: int
    from_status: DraftStatus
    to_status: DraftStatus
    reply_before: str | None
    reply_after: str | None
    safety_flags_before: list[str]
    generation_failure_before: str | None
    reason: str | None
    created_at: str


class DraftView(DraftSummary):
    message_id: int
    generated_reply: str | None
    edited_reply: str | None
    reply: str | None
    review_reason: str
    generation_failure: str | None
    generation_safety_flags: list[str]
    safety_flags: list[str]
    review_events: list[ReviewEventView]


class ClassificationView(BaseModel):
    primary_intent: Intent
    secondary_intents: list[Intent]
    short_summary: str
    needs_review: bool
    review_reason: str


class MessageView(BaseModel):
    id: int
    source_id: str
    candidate_name: str
    message_text: str
    classification: ClassificationView | None
    classification_failure: str | None
    candidate_instruction_detected: bool
    draft: DraftSummary | None


class IntentGroup(BaseModel):
    intent: Intent | Literal["unclassified"]
    messages: list[MessageView]


class BatchGroups(BaseModel):
    batch_id: int
    groups: list[IntentGroup]

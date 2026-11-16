"""Schemas for the two model calls and the application-owned review state."""

from dataclasses import dataclass, field
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, model_validator

from hiring_inbox.classifier import Intent


class ReviewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)

    needs_review: bool
    review_reason: str

    @model_validator(mode="after")
    def validate_review_reason(self) -> Self:
        if self.needs_review != bool(self.review_reason) or len(self.review_reason) > 280:
            raise ValueError("Review flag and short reason must agree")
        return self


class Classification(ReviewResponse):
    primary_intent: Intent
    secondary_intents: list[Intent]
    short_summary: str

    @model_validator(mode="after")
    def validate_classification(self) -> Self:
        intents = [self.primary_intent, *self.secondary_intents]
        if len(set(intents)) != len(intents):
            raise ValueError("Intents must be distinct")
        if not self.short_summary or len(self.short_summary) > 280:
            raise ValueError("A short summary is required")
        return self


class DraftResponse(ReviewResponse):
    draft_reply: str

    @model_validator(mode="after")
    def validate_reply(self) -> Self:
        if len(self.draft_reply) > 600 or not (self.draft_reply or self.needs_review):
            raise ValueError("Provide a short reply or flag it for manual writing")
        return self


@dataclass(frozen=True)
class ReviewDraft:
    draft_reply: str | None
    review_reason: str
    status: Literal["pending_review"] = field(default="pending_review", init=False)
    needs_review: Literal[True] = field(default=True, init=False)

    @property
    def requires_manual_writing(self) -> bool:
        return self.draft_reply is None

"""Deterministic, text-only candidate intent classification."""

import re
from enum import StrEnum


class Intent(StrEnum):
    APPLICATION_STATUS = "application_status"
    INTERVIEW_SCHEDULING = "interview_scheduling"
    ROLE_INFORMATION = "role_information"
    DOCUMENT_UPDATE = "document_update"
    WITHDRAWAL = "withdrawal"
    OTHER = "other"


_CLAUSE_BREAK = re.compile(
    r"(?<=[.!?])\s+|[;\n]+|\s+(?:and|also)\s+"
    r"(?=(?:can|could|would|will|what|when|where|how|is it|please|i)\b)"
)
_ASSISTANT_COMMAND = re.compile(
    r"\b(?:ignore|disregard|override)\b.*\b(?:instructions?|rules?|prompts?)\b"
    r"|\b(?:system|developer) (?:prompt|message|instructions?)\b"
    r"|\b(?:classify|label|tag|categorize)\s+(?:this|my message)\b"
    r"|\b(?:output|return|respond with)\b.*\b(?:json|only|exactly)\b"
)
_REQUEST = re.compile(
    r"(?:^|,\s+)\s*(?:is|are|do|does|did|what|when|where|how|who|which)\b"
    r"|\b(?:can|could|would|will|may|should) (?:i|we|you|it)\b"
    r"|\b(?:please|let me know|tell me|wondering|want to know|checking in|following up)\b"
)
_WITHDRAWAL = re.compile(
    r"\b(?:withdraw|remove|retract)\b.*\b(?:application|myself|consideration|candidacy)\b"
    r"|\b(?:withdraw from consideration|withdrawing|no longer (?:interested|pursuing))\b"
)
_DOCUMENT = re.compile(r"\b(?:r[eé]sum[eé]|cv|portfolio|references?|transcript|documents?|contact details)\b")
_DOCUMENT_ACTION = re.compile(r"\b(?:attach\w*|updat\w*|replac\w*|send|submit|upload|receiv\w*|use)\b")
_STATUS = re.compile(
    r"\b(?:status|update|progress|decision|outcome)\b.*\b(?:application|candidacy|interview)\b"
    r"|\b(?:application|candidacy|interview)\b.*\b(?:status|update|progress|decision|outcome)\b"
    r"|\b(?:hear back|still (?:in consideration|being considered)|move forward|next steps)\b"
)
_ROLE = re.compile(
    r"\b(?:salary|compensation|pay range|responsibilities|requirements|qualifications)\b"
    r"|\b(?:remote|hybrid|on-site|full-time|part-time)\b"
    r"|\b(?:details|information|learn more)\b.*\b(?:role|job|position)\b"
)
_INTERVIEW = re.compile(r"\b(?:interview|screening call)\b")
_INTERVIEW_ACTION = re.compile(
    r"\b(?:schedul\w*|reschedul\w*|confirm\w*|cancel\w*|available|availability|"
    r"move|join|time|date|link|where|when|attend)\b"
)
_INTERVIEW_STATEMENT = re.compile(
    r"\b(?:i (?:can|can't|cannot|won't be able to) (?:attend|join|make)|"
    r"i(?:'m| am) (?:available|unavailable)|works for me|need to (?:reschedule|cancel))\b"
)


def classify_intent(message_text: str) -> Intent:
    """Return the first recognized actionable intent, or ``other``."""
    text = "\n".join(
        line for line in message_text.casefold().splitlines() if not line.lstrip().startswith(">")
    ).replace("’", "'")

    for clause in _CLAUSE_BREAK.split(text):
        if _ASSISTANT_COMMAND.search(clause):
            continue
        if _WITHDRAWAL.search(clause):
            return Intent.WITHDRAWAL
        if _DOCUMENT.search(clause) and _DOCUMENT_ACTION.search(clause):
            return Intent.DOCUMENT_UPDATE
        if clause.rstrip().endswith("?") or _REQUEST.search(clause):
            if _STATUS.search(clause):
                return Intent.APPLICATION_STATUS
            if _ROLE.search(clause):
                return Intent.ROLE_INFORMATION
            if _INTERVIEW.search(clause) and _INTERVIEW_ACTION.search(clause):
                return Intent.INTERVIEW_SCHEDULING
            return Intent.OTHER
        if _INTERVIEW.search(clause) and _INTERVIEW_STATEMENT.search(clause):
            return Intent.INTERVIEW_SCHEDULING

    return Intent.OTHER

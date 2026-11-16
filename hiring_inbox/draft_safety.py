"""Conservative checks for claims when no verified recruiting facts are supplied."""

import re
import unicodedata


_ASSISTANT_INSTRUCTIONS = re.compile(
    r"\b(?:ignore|override|disregard)\b[^.!?\n]{0,65}\b(?:prompts?|instructions?|rules?)\b"
    r"|\b(?:system|developer) (?:prompt|instructions?)\b"
    r"|\b(?:label|classify|categorize|tag) (?:this (?:message|email)|my (?:message|email))\b"
    r"|\b(?:treat|interpret) this (?:email|message|text) as (?:admin\w*|system|developer)\b"
    r"|\[(?:automation note|for the (?:automated reviewer|routing bot|assistant))\]"
    r"|\b(?:bypass|skip) (?:human |reviewer )?approval\b"
)


_CHECKS = {
    "date": re.compile(
        r"\b(?:mon(?:day)?|tue(?:sday)?|wed(?:nesday)?|thu(?:rsday)?|fri(?:day)?|"
        r"sat(?:urday)?|sun(?:day)?|today|tomorrow|yesterday|tonight|"
        r"(?:this|next)\s+(?:morning|afternoon|evening|week|month|year))\b"
        r"|\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|"
        r"aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\.?\s+\d{1,2}\b"
        r"|\b\d{1,2}(?:st|nd|rd|th)?\s+(?:jan\w*|feb\w*|mar\w*|apr\w*|may|jun\w*|"
        r"jul\w*|aug\w*|sep\w*|oct\w*|nov\w*|dec\w*)\b"
        r"|\b\d{1,4}[-/.]\d{1,2}(?:[-/.]\d{1,4})?\b|\b(?:19|20)\d{2}\b"
    ),
    "time": re.compile(
        r"\b(?:\d{1,2}:\d{2}|\d{1,2}\s*(?:a\.?m\.?|p\.?m\.?)|\d{1,2}\s*(?:utc|gmt)|"
        r"noon|midnight|(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\s+o'clock)\b"
    ),
    "monetary_amount": re.compile(
        r"[$€£¥₹₨]\s*\d|\b(?:usd|eur|gbp|pkr|inr|cad|aud)\s*\d"
        r"|\b\d[\d,.]*\s*(?:k|usd|eur|gbp|pkr|inr|cad|aud|dollars?|euros?|pounds?|rupees?)\b"
        r"|\b(?:salary|pay|compensation|stipend|package)\s+(?:is|of|starts at|ranges? from)\s+\d"
        r"|\b(?:six|seven)[ -]figures?\b"
    ),
    "hiring_commitment": re.compile(
        r"\b(?:you're|you are|you have been|you've been)\s+(?:officially\s+)?"
        r"(?:hired|selected|shortlisted|rejected|approved|moving forward|advancing)\b"
        r"|\byou (?:got the (?:job|role|position)|passed (?:the|your) (?:interview|screening|assessment))\b"
        r"|\b(?:your application (?:has been|was|is) (?:approved|accepted|rejected)|"
        r"the (?:role|job|position) is yours|welcome aboard|moving (?:you|your application) forward)\b"
        r"|\b(?:we've|we have|we are|we're|we will|we'll)\s+(?:already\s+)?"
        r"(?:selected|hired|approved|rejected|shortlisted|scheduled|rescheduled|booked|"
        r"schedule|reschedule|book|pay|hire|offer you|extend (?:you )?an offer|send (?:you )?(?:an|the) offer)\b"
        r"|\b(?:pleased|excited|delighted) to offer (?:you|the)\b"
        r"|\b(?:interview|screening|meeting|panel|appointment|slot)\b[^.!?\n]{0,60}"
        r"\b(?:is|has been|was) (?:confirmed|scheduled|rescheduled|booked|cancelled|canceled)\b"
        r"|\byour withdrawal (?:is|was|has been) (?:processed|confirmed|accepted)\b"
    ),
    "company_policy": re.compile(
        r"\b(?:our (?:company |hiring )?policy (?:is|requires|allows|states)|"
        r"(?:we|the company) (?:require|guarantee)\b)"
        r"|\b(?:office attendance|remote work|work hours)\s+(?:can |may )?(?:differ|vary)\b"
    ),
    "unsupported_followup": re.compile(
        r"\b(?:we|i)(?:'ll| will)\s+(?:keep you informed|follow up|let you know|"
        r"review (?:your|the) (?:application|status)|update (?:our|the|your) (?:records|application)|"
        r"process (?:the|your) (?:request|withdrawal)|cancel (?:the|your) (?:interview|meeting|panel))\b"
    ),
    "assistant_instruction": _ASSISTANT_INSTRUCTIONS,
}


def _normalize(text: str) -> str:
    return unicodedata.normalize("NFKC", text).casefold().replace("’", "'")


def screen_candidate_text(message: str) -> tuple[str, bool]:
    """Remove recognizable assistant-directed segments and flag for manual writing."""
    segments = re.split(r"(?<=[.!?])\s+|[\r\n]+", message)
    kept = [segment for segment in segments if not _ASSISTANT_INSTRUCTIONS.search(_normalize(segment))]
    detected = len(kept) != len(segments)
    return (" ".join(kept).strip() if detected else message), detected


def draft_safety_flags(draft: str) -> tuple[str, ...]:
    normalized = _normalize(draft)
    return tuple(name for name, pattern in _CHECKS.items() if pattern.search(normalized))

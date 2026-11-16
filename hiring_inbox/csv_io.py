"""Parse bounded imports and render spreadsheet-safe CSV exports."""

import csv
import hashlib
import io
import json
import re
import unicodedata
from dataclasses import dataclass


MAX_CSV_BYTES = 1_048_576
MAX_MESSAGES = 50
MAX_MESSAGE_LENGTH = 12_000
_REQUIRED = ("message_id", "candidate_name", "message_text")
_IGNORED_METADATA = {"expected_intent", "secondary_intent", "is_adversarial", "split"}
_SOURCE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_FORMULA_START = re.compile(r"^[\s\ufeff\u200b-\u200f]*[=+@-]")


@dataclass(frozen=True)
class ImportedMessage:
    source_id: str
    candidate_name: str
    message_text: str


def parse_import(body: bytes) -> list[ImportedMessage]:
    messages = []
    seen = set()
    try:
        reader = csv.reader(io.StringIO(body.decode("utf-8-sig"), newline=""), strict=True)
        header = next(reader, [])
        if len(set(header)) != len(header) or not set(_REQUIRED) <= set(header):
            raise ValueError("CSV requires distinct message_id, candidate_name, and message_text columns.")
        if set(header) - set(_REQUIRED) - _IGNORED_METADATA:
            raise ValueError("CSV contains an unsupported column.")
        id_col, name_col, text_col = (header.index(column) for column in _REQUIRED)
        for row in reader:
            if not row:
                continue
            location = f"CSV record ending on line {reader.line_num}"
            if len(row) != len(header) or any(_CONTROL.search(field) for field in row):
                raise ValueError(f"{location} is malformed.")
            source_id, name, text = row[id_col].strip(), row[name_col].strip(), row[text_col].strip()
            if not _SOURCE_ID.fullmatch(source_id):
                raise ValueError(f"{location} has an invalid message_id.")
            if source_id in seen:
                raise ValueError(f"{location} repeats a message_id.")
            if not name or len(name) > 200 or "\r" in name or "\n" in name:
                raise ValueError(f"{location} has an invalid candidate_name.")
            if not text or len(text) > MAX_MESSAGE_LENGTH:
                raise ValueError(f"{location} has an invalid message_text length.")
            if len(messages) == MAX_MESSAGES:
                raise ValueError(f"CSV can contain at most {MAX_MESSAGES} messages.")
            seen.add(source_id)
            messages.append(ImportedMessage(source_id, name, text))
    except (UnicodeDecodeError, csv.Error):
        raise ValueError("CSV must be well-formed UTF-8.") from None
    if not messages:
        raise ValueError("CSV contains no candidate messages.")
    return messages


def fingerprint(messages: list[ImportedMessage]) -> str:
    canonical = sorted((row.source_id, row.candidate_name, row.message_text) for row in messages)
    raw = json.dumps(canonical, ensure_ascii=False, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def export_csv(rows: list[tuple[str, str, str, int, int, str]]) -> str:
    def safe_cell(value: str | int) -> str | int:
        if isinstance(value, str):
            normalized = unicodedata.normalize("NFKC", value)
            if normalized.startswith(("\t", "\r", "\n")) or _FORMULA_START.match(normalized):
                return "'" + value
        return value

    output = io.StringIO(newline="")
    writer = csv.writer(output, quoting=csv.QUOTE_ALL)
    writer.writerow(("message_id", "candidate_name", "primary_intent", "draft_id", "revision", "reply"))
    writer.writerows([safe_cell(value) for value in row] for row in rows)
    return output.getvalue()

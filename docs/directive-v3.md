# Implementation directive v3 · Local review backend

Use FastAPI, Pydantic, SQLAlchemy, and a local SQLite file. The Milestone 2 pipeline supplies classification, review notes, draft text, safety flags, and failure codes through its existing interface. Milestone 1 and 2 evidence and evaluation behavior are preserved.

## Run locally

Use Python 3.11+ and one Uvicorn worker on loopback. The service trusts its local caller to perform human review. Any local caller with access to the API can inspect candidate messages and act on revisions. Use the existing `.env.example` for Groq configuration. The default SQLite file is `var/inbox.sqlite3`. Set `INBOX_DB_PATH` in the process environment to use a different file. Keep candidate data and generated exports out of Git.

```sh
uv venv --python 3.11 .venv
uv pip sync --python .venv/bin/python requirements.txt
env -u GROQ_LOG .venv/bin/python -m uvicorn hiring_inbox.api:app --host 127.0.0.1 --workers 1
```

Use `http://127.0.0.1:8000/docs` to inspect the OpenAPI contract. For import, send a raw UTF-8 CSV body using `Content-Type: text/csv`. The required headers are `message_id`, `candidate_name`, and `message_text`. The four evaluation metadata columns are optional and ignored. The upload limit is 1 MiB and 50 messages. After trimming outer whitespace, IDs must be 1–64 characters, start with an ASCII letter or digit, and contain only ASCII letters, digits, `.`, `_`, or `-`. Names can be up to 200 characters and message text up to 12,000 characters. Duplicate IDs and malformed rows invalidate the entire upload. Use a separate import file for backend work and keep the original evaluation fixture untouched.

```sh
curl -fsS -H 'Content-Type: text/csv' --data-binary @candidate-messages.csv http://127.0.0.1:8000/batches
curl -fsS -X POST http://127.0.0.1:8000/batches/1/process
curl -fsS http://127.0.0.1:8000/batches/1/groups
curl -fsS http://127.0.0.1:8000/drafts/1
# Review the candidate message and current reply before approving the displayed revision.
curl -fsS -H 'Content-Type: application/json' -d '{"revision":1}' http://127.0.0.1:8000/drafts/1/approve
curl -fsS -o approved.csv http://127.0.0.1:8000/batches/1/export
```

Replace the example IDs and revision with those returned by the API. In a separate client, use the status endpoint to follow an active processing request.

## Endpoints

| Method and path | Behavior |
| --- | --- |
| `POST /batches` | Validate and import a CSV. Returns `201` for a new batch or `200` with `duplicate: true` and the existing batch ID for an identical import. |
| `POST /batches/{id}/process` | Process remaining messages serially. Returns current status for a finished batch. |
| `GET /batches/{id}/status` | Return processing, classification, review, manual-writing, and regeneration counts. |
| `GET /batches/{id}/groups` | Return messages grouped by current primary intent, including `unclassified` as needed. |
| `GET /drafts/{id}` | Read generated and edited text, effective reply, revision, flags, failure, and review history. |
| `PATCH /drafts/{id}` | Write a replacement `reply` and increment `revision`. Reset to `pending_review`. |
| `POST /drafts/{id}/approve` | Approve the named pending revision when a reply exists and passes current checks. |
| `POST /drafts/{id}/reject` | Reject the named pending or approved revision and remove its export eligibility. |
| `POST /drafts/{id}/regenerate` | Reserve a pending revision and clear approval before calling Groq. Store the result on the same draft record. |
| `GET /batches/{id}/export` | Return an attachment with only current approved, eligible replies. Returns a header-only CSV when no replies qualify. |

All review mutations require a JSON `revision` integer. An optional `reason` is recorded in the history. `PATCH` also requires a nonblank `reply` of at most 1,200 characters. Unknown records return `404`. Conflicts such as stale revisions, an ineligible transition, or busy processing return `409`. Invalid requests return `422`, oversized CSV uploads return `413`, mislabelled upload media returns `415`, and unavailable Groq configuration returns `503` for work requiring the provider.

## Persistence and review decisions

- `batches` stores an import fingerprint and processing status. Fingerprints use normalized candidate data sorted by source ID. CSV row order and fixture metadata do not affect the fingerprint. Distinct batches can reuse a source ID.
- `messages` stores the source ID, candidate name, text, primary intent, structured classification, and classification failure. Intent groups are derived from these rows.
- `drafts` stores one current record per message, with generated and edited replies, current and approved revision numbers, safety flags, and failure or manual-writing information. A safe manual edit can replace withheld text. The original generation flags remain visible until regeneration and are recorded in review history.
- `review_events` records edits, approvals, rejections, and regenerations with timestamps, revision and status changes, before and after replies, prior safety findings, and any operator reason. A regeneration records the previous revision before requesting Groq and fills in the replacement when processing returns.
- Review changes use conditional database updates. The database constrains an approval to the matching revision, and export also checks the status, revision and current safety rules. Editing or regenerating clears approval. Rejected, blocked, in-progress, and unreviewed revisions are ineligible. The CSV exporter quotes fields and prefixes formula-like cells with an apostrophe. Spreadsheet applications can rewrite escaping when saving and reopening CSV files. [OWASP CSV injection](https://community.owasp.org/attacks/CSV_Injection)
- Processing uses one generation slot across batches and regenerations. It commits each message separately and preserves peer results when an individual message fails. The next startup marks partial batches `interrupted` and clears interrupted regenerations to manual writing. Reprocess an interrupted batch to resume from committed records. Retry a failed message by regenerating its draft. A provider call interrupted before its database commit can be repeated.

## Verification

```sh
.venv/bin/python -B -m pytest -q -p no:cacheprovider --ignore=tests/test_dataset.py
uv pip check --python .venv/bin/python
```

API tests use FastAPI TestClient, temporary SQLite files, and mocked Groq responses. The Milestone 1 dataset test opens the entire evaluation fixture and is kept out of this run. The backend test run uses synthetic imports and makes zero live Groq requests. The app holds processing requests open while it works and has no distributed worker or authentication. Pattern checks cannot establish reply accuracy or safety on their own. Human review remains required.

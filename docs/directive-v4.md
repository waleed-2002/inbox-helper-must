# Implementation directive v4 · Recruitment workspace

The Next.js workspace uses the existing local FastAPI API and SQLite database. See the [UI design](ui-design.md) for layout, tokens, components, and accessibility choices. Keep the backend authoritative for safety, approval, and export.

## Run locally

Use Python 3.11+ and Node.js 22 LTS. Run the two processes in separate terminals from the repository root.

```sh
# On first setup, create .venv and configure the root .env from .env.example.
uv venv --python 3.11 .venv
uv pip sync --python .venv/bin/python requirements.txt
env -u GROQ_LOG INBOX_WEB_ORIGIN=http://127.0.0.1:3000 \
  .venv/bin/python -m uvicorn hiring_inbox.api:app --host 127.0.0.1 --workers 1
```

```sh
npm --prefix web ci
npm --prefix web run dev
```

Open `http://127.0.0.1:3000`. The browser defaults to `http://127.0.0.1:8000` for FastAPI. Set `NEXT_PUBLIC_INBOX_API_URL` in the frontend process environment or `web/.env.local` for a different API port. Production builds embed the value, so configure it before building. Set the server's `INBOX_WEB_ORIGIN` to the exact browser origin, including hostname and port. CORS is off by default and permits only the configured HTTP loopback origin. The Groq key belongs in the root backend configuration.

## Review workflow

1. Import a UTF-8 CSV using `message_id,candidate_name,message_text` headers. The backend validates the full file and reports invalid columns, duplicate IDs, malformed rows, and limits. Duplicate uploads reopen the existing batch. The sidebar discovers earlier batches through `GET /batches`, which returns `{batches: [{batch_id, created_at, message_count}]}` newest first.
2. Process the batch and follow the polled status. The frontend holds the processing request open and updates the groups from FastAPI as results arrive. After a disconnect, wait for current batch status before retrying.
3. Read the original message, safety notes and current revision. Save changes before explicitly approving. Rejection and regeneration can record an optional reason. After a `409`, compare the current reply with preserved local edits before deciding what to save or approve.
4. Open the Outbox and export eligible approvals for the selected batch. The download uses the server's CSV endpoint. Safety checks and the current approved revision determine which rows the server exports.

The local single-user and single-worker restrictions still apply. Keep candidate information and downloaded CSVs out of Git. Existing request and response details are in the [Milestone 3 API contract](directive-v3.md), and the running backend serves OpenAPI at `http://127.0.0.1:8000/docs`.

## Verification

```sh
npm --prefix web run lint
npm --prefix web run typecheck
npm --prefix web run build
.venv/bin/python -B -m pytest -q -p no:cacheprovider --ignore=tests/test_dataset.py
```

Use separately authored fictional CSVs and temporary SQLite for browser tests. Inject a deterministic provider through `create_app` so the tests exercise the existing pipeline and persistence without using live credentials. Keep the Milestone 1 full-fixture tests out of these runs to leave the holdout unseen.

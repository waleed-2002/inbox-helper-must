# inbox-helper-must

Local recruitment workspace for CSV import, Groq triage, human draft review, and approved CSV export. The backend runs on FastAPI and SQLite. The browser workspace runs on Next.js.

## Project structure

| Location | Responsibility |
| --- | --- |
| `hiring_inbox/api.py` and `hiring_inbox/api_models.py` | FastAPI startup, routes, and their request and response contracts. |
| `hiring_inbox/review_service.py` | Batch processing, draft revisions, approval, and export eligibility. |
| `hiring_inbox/database.py` and `hiring_inbox/csv_io.py` | SQLite persistence and CSV validation and serialization. |
| `hiring_inbox/pipeline.py` and its supporting modules | Classification and drafting, the Groq adapter, model response validation, and safety checks. |
| `web/src/app/` and `web/src/features/inbox/` | Next.js routing and the inbox feature, including its API client, workspace, and review and import components. |
| `web/src/components/ui/` and `web/src/lib/` | Shared UI controls and frontend utilities. |
| `tests/`, `data/`, and `evidence/` | Python tests, the fictional evaluation fixture, and recorded evaluation results. |

The browser calls the backend over HTTP. FastAPI owns validation, approval, and export eligibility. Python owns database access and Groq credentials.

## Run locally

From the repository root, set up the backend on Python 3.11 or later and configure Groq with the root `.env.example`.

```sh
uv venv --python 3.11 .venv
uv pip sync --python .venv/bin/python requirements.txt
env -u GROQ_LOG INBOX_WEB_ORIGIN=http://127.0.0.1:3000 \
  .venv/bin/python -m uvicorn hiring_inbox.api:app --host 127.0.0.1 --workers 1
```

In a second terminal with Node.js 22 LTS:

```sh
npm --prefix web ci
npm --prefix web run dev
```

Open the [recruiter workspace](http://127.0.0.1:3000) or the [API reference](http://127.0.0.1:8000/docs). Use the exact loopback hostname shown here so it matches the configured browser origin. The workspace is intended for one trusted local operator.

See the [Milestone 4 directive](docs/directive-v4.md) for CSV format, review steps, configuration, and test commands, and the [UI design guide](docs/ui-design.md) for the visual system.

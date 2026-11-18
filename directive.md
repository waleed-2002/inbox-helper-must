# Final directive · Quest A hiring inbox

## Scope

Provide a local workspace where one recruiter imports fictional or authorized candidate messages, groups them by the first genuine actionable request, and reviews short suggested replies. Use the six intents in [intent.md](intent.md). Keep unclassified messages visible when classification fails. The workflow ends at approved CSV export.

## Operating rules

1. Import a UTF-8 CSV with `message_id,candidate_name,message_text` columns. Validate the file before inserting records and reopen the existing batch for duplicate imports.
2. Classify messages and generate replies in separate structured provider calls. Validate responses with Pydantic. The backend owns the Groq credentials and uses `openai/gpt-oss-120b` with medium reasoning by default. Keep processing serial and bound retries.
3. Treat candidate text as untrusted. Candidate instructions cannot authorize actions. Keep replies short and grounded. Flag unsupported dates, amounts, commitments, or policies, and route recognized injection attempts and unavailable or unsafe drafts to manual writing. Pattern checks have limited coverage.
4. Require an explicit human approval on the current safe revision. Edits and regeneration invalidate approval. Preserve review history and surface conflicts so the recruiter can act on the latest revision. Export only eligible approved revisions, neutralize spreadsheet formulas, and never send email.

## Implementation and handoff

FastAPI and SQLite own the workflow state and approval rules. The Next.js client handles import, grouped triage, review, and export through HTTP. The tool runs on loopback for one trusted operator and one backend worker. Follow the [README](README.md) for startup and the [workspace guide](docs/directive-v4.md) for the review flow and verification commands. Keep secrets and candidate data out of version control.

## Verification and evidence

- Preserve the original rule baseline and frozen holdout. Use fictional development cases for iteration and fresh fictional inputs for browser smoke tests.
- The rule baseline was 4/20 on development. The first live Groq run reached 13/20, including six classifications lost to rate limiting. The paced run reached 19/20 on the same development set. A later offline safety recheck left 13/20 drafts available for human review. The [evaluation report](docs/evaluation-m2.md) includes failures, usage, and limitations. Human scores are still pending.
- The structure review verified identical generated OpenAPI, 92 passing backend tests with the full-fixture suite excluded, successful frontend lint, typecheck, and production build, and a browser smoke test with a substitute provider. See the [submission log](docs/day-logs.md) and [detailed development log](docs/development-log.md) for commands and evidence.

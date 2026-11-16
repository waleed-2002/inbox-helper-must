Continue MUST Company's Quest A from Milestone 2 (commit 24bcfc7).

Inspect AGENTS.md, intent.md, existing pipeline, tests and evaluation evidence. Preserve all verified results.

MILESTONE 3: FastAPI + SQLite + Human Review

GOAL:
Build a reliable backend that imports candidate messages, processes them using the existing Groq pipeline, groups them by intent, and enforces human review before approved replies can be exported.

STACK:
- FastAPI + Pydantic
- SQLite + SQLAlchemy
- Existing Groq pipeline (gpt-oss-120b, medium reasoning)
- pytest
- Minimal dependencies, pinned versions

IMPLEMENT:

1. Database:
   - batches: import and processing status
   - messages: candidate information, content and classified intent
   - drafts: generated text, edited text, status and revision
   - review_events: edit, approve, reject and regenerate history
   - Derive intent groups dynamically; no groups table needed.

2. API:
   POST /batches             Import CSV
   POST /batches/{id}/process
   GET  /batches/{id}/status
   GET  /batches/{id}/groups
   GET  /drafts/{id}
   PATCH /drafts/{id}
   POST /drafts/{id}/approve
   POST /drafts/{id}/reject
   POST /drafts/{id}/regenerate
   GET  /batches/{id}/export

3. Human-review rules:
   - Every generated draft starts as pending_review.
   - Approval requires an explicit API action.
   - Rejected or unsafe drafts cannot be exported.
   - Editing or regenerating an approved draft invalidates approval.
   - Export only the currently approved revision.
   - Never send actual emails.
   - Enforce all rules in backend logic, not just the future UI.
   - Include meaningful review-event history.

4. Processing:
   - Reuse the existing Groq pipeline without modifying its verified evaluation behavior.
   - Validate CSV columns, IDs, sizes and malformed rows.
   - Prevent duplicate processing and duplicate records.
   - Handle individual message failures without losing the entire batch.
   - Use simple bounded processing; avoid Celery, Redis or unnecessary infrastructure.
   - Clearly report processing and review status.

5. Security:
   - Treat candidate messages as untrusted.
   - Preserve LLM safety flags and manual-writing states.
   - Prevent CSV formula injection in exported text.
   - Avoid SQL injection and unauthorized state transitions.
   - No authentication or real sending; document the local single-user limitation.
   - Never log or expose API credentials.

6. Testing:
   - Test API endpoints with FastAPI TestClient.
   - Use temporary SQLite databases and mocked Groq responses.
   - Verify state transitions, approval, rejection, regeneration, exports, duplicates and failures.
   - Include tests proving unapproved or stale revisions cannot be exported.
   - Run existing tests safely without exposing the frozen holdout.

7. Documentation:
   - Save this prompt as prompts/03-milestone-3.md.
   - Update the development directive and real work log.
   - Document database decisions, API endpoints and test commands.
   - Preserve original Milestone 1 and 2 evidence.
   - Do not invent hours, human review scores or results.

CONSTRAINTS:
- Do not implement Next.js yet.
- Do not add authentication, email integration or external databases.
- Do not change frozen holdout examples or evaluation results.
- Keep implementation small, testable and easy to run locally.

WORKFLOW:
Briefly outline the plan, implement incrementally, run tests, fix failures, and commit verified changes.

FINAL REPORT:
- Files created/changed
- API endpoints implemented
- Test results
- Approval/export safety verification
- Bugs identified and fixed
- Remaining limitations
- Recommended Milestone 4

STOP after Milestone 3 for review.

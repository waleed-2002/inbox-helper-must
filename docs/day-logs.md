# Quest A day logs

The planning assumption is four active build hours over five days. The limit is unconfirmed. Enter actual active time and personal reflections in the blank fields.

## Day 1 · 2026-11-16 (PKT)

**Active hours**

**Personal reflection**

### Verified work

| Commit | Work |
| --- | --- |
| `315b6b3` | Initialized the project specification, Codex instructions, implementation directive, and saved prompt. |
| `c775b79` | Implemented the deterministic classifier and verified 20 independent unit cases before authoring evaluation data. |
| `7ba021c` | Committed 30 fictional messages with provisional labels and froze holdout IDs 21–30. |
| `ca8b2e9` | Added the split evaluator and dataset validation tests. This is the code snapshot used for the baseline. |

Observed session timestamps span 22:36:50–22:41:41 PKT from environment setup through baseline verification.

### Failures and corrections

- The default `python3` reported Python 3.15.2 and lacked pytest. Created an ignored local environment with Python 3.11.14 and installed pytest 9.2.0 using `uv`.
- The first classifier test run produced 19 passes and 1 failure. Splitting a compound question at “and” removed the first request's trailing question mark, so the classifier returned the second intent. Recognizing clause-initial question words fixed the case. The next run passed all 20 tests before the dataset was created.

### Verification

| Command | Result |
| --- | --- |
| `.venv/bin/python -m pytest -q` | 24 passed in 0.01 s. Dataset tests validated both split structures without scoring candidate messages. |
| `.venv/bin/python -m hiring_inbox.evaluate --split all` | Initial baseline, including the single holdout scoring run. The matrix totals, diagonal, and counts of reported misses reconcile for both splits. |

Frozen fixture SHA-256 `8adf8df7357435b82aee990f6b5ccaca08001c0c7603332342dbb337a5386216`.

| Split | Correct | Accuracy | Misclassified IDs |
| --- | --- | --- | --- |
| Development | 4/20 | 20.0% | 1–5, 7–8, 11–16, 18–20 |
| Holdout | 2/10 | 20.0% | 21–25, 27–28, 30 |

Every prediction was `other`. This table records the populated column of both confusion matrices. The remaining predicted columns contain zeros.

| Expected intent | Dev predicted `other` | Holdout predicted `other` |
| --- | ---: | ---: |
| `application_status` | 3 | 2 |
| `interview_scheduling` | 3 | 2 |
| `role_information` | 4 | 2 |
| `document_update` | 4 | 1 |
| `withdrawal` | 2 | 1 |
| `other` | 4 | 2 |

### Review notes

- The rules matched direct phrasing in unit cases. In the dataset, indirect phrasing, references across sentences, and vocabulary outside the patterns caused intent misses. The baseline classifier and frozen fixture stayed at their pre-evaluation versions.
- Review #7’s secondary `interview_scheduling` label. It assumes “our conversation” refers to a recruiting interview. Review whether #13’s explicit calendar cancellation warrants a secondary label when it accompanies a withdrawal.
- Review #14’s `role_information` label, which interprets “budget for this hire” as compensation. #9 and #26 are provisionally `other` because both refer to missing context. Record adjudications separately from the scored fixture.
- Primary intent is the only scored field. The sample is small and synthetic, and candidate commands are represented by a few examples. The results are insufficient to estimate production performance or security.

## Day 2 · 2026-11-16 (PKT)

**Active hours**

**Personal reflection**

### Verified work

| Commit | Work |
| --- | --- |
| `e923794` | Ignored local environment files and common secret files. Verified `.env` was neither tracked nor staged and `.env.example` was eligible for tracking. |
| `c9b61b3` | Added Groq SDK integration, strict schemas, the pending-review pipeline, and development-only evaluation. |
| `38c1640` | Tested bounded retries and expanded hiring-commitment checks. |
| `674786a` | Saved the first live run with predictions, pending drafts, failures, and token usage. |
| `f34715b` | Screened assistant-directed candidate text, expanded draft safety checks, and added serial request pacing. |
| `63be35d` | Added regression cases and safety checks for invented recruiting disclosure policies. |

Before implementation, a development-only rerun reproduced 4/20 correct and 20 predictions of `other`. Traces of #1, #8, and #11 showed narrow keyword coverage and the early fallback on an unmatched request. The approved secondary label for #7 is blank in Milestone 2 scoring. #13 and #14 retain their original labels. The fixture and Milestone 1 results were preserved.

### Failures and corrections

- The first mocked run passed 45 cases and failed 1. The pinned SDK rejected `content_filter` in its response enum, so the provider adapter now maps that case to a refusal before returning a sanitized failure.
- Before the credential was configured, the evaluator skipped live requests. After the user configured the key, the first live run reported 13/20 correct, including six HTTP 429 classification failures and one wrong intent. Twelve drafts reached pending review, including two influenced by assistant-directed text (#10 and #20). Two additional drafts were withheld for date or time signals.
- The revised pipeline screens recognizable assistant-directed segments from classification input and skips drafting for detected attempts. Affected messages require manual writing. The draft checks also cover more unverified promises. The revised evaluator uses one worker and an eight-second minimum interval between logical requests.
- The paced run produced 15 pending drafts. Assistant review found unsupported disclosure claims in #8 and #14. Reapplying the new guard offline withheld both, leaving 13 drafts available for human review. The live evidence was preserved.

### Verification

- `.venv/bin/python -B -m pytest -q -p no:cacheprovider tests/test_classifier.py tests/test_ai_pipeline.py tests/test_ai_evaluation.py` passed 60 tests. The legacy dataset test file remains intact and was excluded because it opens the full fixture.
- `uv pip check --python .venv/bin/python` reported compatible pinned dependencies.
- `env -u GROQ_LOG .venv/bin/python -B -m hiring_inbox.evaluate_ai --output evidence/milestone-2-dev.json` recorded the first development run at 23:30:58 PKT. Reported usage cost about $0.00660.
- The same command with output `evidence/milestone-2-dev-paced.json` recorded the paced run at 23:35:34 PKT. It scored 19/20 (95%) without API failures. All three flagged injection cases went to manual writing. All 37 calls reported usage, estimated at $0.00802.
- Independently reconciled message IDs, pending-review status, correct predictions, confusion counts, token totals, and estimated cost in both live artifacts. Results and the blank human-review rubric are in `docs/evaluation-m2.md` and `docs/reply-review-m2.md`.

## Day 3 · 2026-11-16–17 (PKT)

**Active hours**

**Personal reflection**

### Verified work

| Commit | Work |
| --- | --- |
| `d90e603` | Added the four SQLite tables, foreign keys, pinned backend dependencies, and bounded CSV parsing and export. Verified table creation and foreign key enforcement on a temporary file. |
| `052c654` | Added the FastAPI review endpoints, serial processing, individual failure recovery, revision-checked transitions, and approval-only export. |

### Verification

- `.venv/bin/python -B -m pytest -q -p no:cacheprovider --ignore=tests/test_dataset.py` passed 89 tests, including 29 new API cases. The preserved dataset tests were excluded to keep the frozen holdout unseen.
- A loopback Uvicorn run using a temporary database verified the OpenAPI document, CSV import, imported status, and a header-only export before approval. Groq was mocked in tests and was not called in the smoke run.
- Verified concurrent generation and approval behavior, invalidation after edits and regeneration, approval of a safe manual replacement, rejection of unsafe or stale revisions, and formula neutralization in serialized CSV cells.
- `uv pip check --python .venv/bin/python` reported compatible pinned dependencies. Starlette emitted one TestClient deprecation warning for its HTTPX compatibility adapter. The adapter worked in the pinned test environment.

Original pipeline code, dataset, and evaluation artifacts remain at their Milestone 2 versions. No human review scores were recorded.

## Day 4 · 2026-11-17 (PKT)

**Active hours**

**Personal reflection**

### Verified work

| Commit | Work |
| --- | --- |
| `0f88feb` | Ran the published UI/UX Pro Max design-system, Next.js, and keyboard focus guidance and documented the selected tokens and layout. |
| `d5516c1` | Added batch discovery and opt-in loopback CORS with three regression tests. |
| `02fc1c5` | Built the responsive Next.js workspace with CSV import, processing progress, grouped inbox, revision-aware review, and approved-only Outbox. |

### Verification

- `npm ci --offline --no-fund --no-audit`, `npm run lint`, `npm run typecheck`, and `npm run build` passed in `web/`. The install reported an ESLint 9 deprecation notice. The Next.js lint configuration uses plugins with ESLint 9 peer support.
- `.venv/bin/python -B -m pytest -q -p no:cacheprovider --ignore=tests/test_dataset.py` passed 92 tests with the existing Starlette TestClient warning. `uv pip check --python .venv/bin/python` found compatible Python dependencies.
- Playwright Chromium exercised the production-built UI and Uvicorn with temporary SQLite and a deterministic Groq provider substitute. The desktop smoke imported four new fictional messages, observed one processing request, rejected malformed input, reopened a duplicate import, and downloaded an approved CSV containing only the approved reply.
- In the same smoke test, unsafe and rejected drafts stayed ineligible. Editing and in-flight regeneration removed approval. A competing edit triggered a real `409`, preserved the local text, and required a new save and approval before export. Candidate markup remained plain text.
- At 375px and in landscape, verified the keyboard drawer, focus restoration, intent filtering, search, and lack of horizontal overflow. Also verified reduced motion, batch discovery from a fresh tab, recovery from a failed read, and disabled processing retry until the server returned batch status.

### Findings and corrections

- ESLint initially warned about an anonymous PostCSS config export. Assigned the configuration to a named variable before exporting it and reran lint cleanly.
- The first browser run logged a missing favicon. Added the application icon and verified that the browser no longer requested the missing resource.
- Review of the disconnected-processing path showed the old status could briefly enable retry. The UI now keeps retry disabled while a replacement status request is pending. The browser smoke delayed that request and verified the lockout.

The existing Groq pipeline, dataset, holdout, and evaluation artifacts were preserved. The browser runs made no live Groq calls and recorded no human review scores.

## Day 5

- **Date**
- **Active hours**
- **Work and commit references**
- **Commands and actual results**
- **Failures and corrections**
- **Personal reflection**

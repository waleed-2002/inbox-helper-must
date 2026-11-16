# Implementation directive v2

## Approved decisions

Use separate Groq Cloud calls for classification and drafting with `openai/gpt-oss-120b`, medium reasoning effort, strict JSON Schema, and local Pydantic validation. Keep the original classifier, fixture, and baseline for comparison. The approved #7 secondary label is blank for this evaluation. #13 remains withdrawal with interview scheduling as secondary, and #14 remains provisionally role information. Apply the #7 decision in the evaluator without editing the frozen fixture.

## Runtime behavior

- Create `GroqProvider` with process environment settings or a local `.env`. The process environment takes precedence. `.env.example` documents the supported settings. Keep keys out of logs, prompts, and version control. The provider uses Groq's official endpoint and records sanitized failure codes.
- Call `process_message(provider, candidate_message)` from future backend code. Requests place candidate text in a JSON user message and keep instructions in the system message. The draft call receives only the original candidate text and validated primary intent from classification.
- Screen out recognizable assistant-directed segments before classification. A detected instruction forces classification review and manual writing. The pipeline skips automated drafting for that message, including when a genuine recruiting request remains.
- The pipeline supplies no verified recruiting facts. It withholds drafts flagged for dates, times, monetary amounts, hiring commitments, company policy claims, unsupported follow-up promises, or assistant-directed instructions. Missing or failed responses also require manual writing. An unsuccessful classification skips the draft request.
- Every returned draft has an application-owned `pending_review` status. An uncertainty reason from either call is visible to the reviewer. The pipeline provides no send or approval operation. Pattern checks can miss claims or flag benign text, so a reviewer must verify every reply.
- The evaluator calls Groq serially with at least eight seconds between logical request starts. The SDK applies a 15-second request timeout and up to two retries on transient failures with exponential backoff or a server retry hint. The first live run used two workers and encountered six rate-limit failures. [Groq Python SDK](https://github.com/groq/groq-python#retries), [Groq rate limits](https://console.groq.com/docs/rate-limits)

## Verification and evaluation

Install the pinned dependencies into the local Python 3.11+ environment, then run the independent classifier tests and mocked pipeline tests. Keep the original full-fixture tests intact and exclude them from runs where the holdout must stay unseen.

```sh
uv pip sync --python .venv/bin/python requirements.txt
.venv/bin/python -B -m pytest -q -p no:cacheprovider tests/test_classifier.py tests/test_ai_pipeline.py tests/test_ai_evaluation.py
mkdir -p evidence
env -u GROQ_LOG .venv/bin/python -B -m hiring_inbox.evaluate_ai --output evidence/milestone-2-dev-new.json
```

The last command consumes only development IDs 1–20 and skips before loading the dataset if the credential is unavailable. Use a new output path for each run. A missing classification counts as an incorrect prediction. Review pending replies using the manual rubric in `docs/reply-review-m2.md` and leave grades blank until a person scores them.

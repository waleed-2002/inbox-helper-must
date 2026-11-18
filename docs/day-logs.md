# Quest A · Five-day log

I worked on the quest across three calendar days, November 16–18, 2026 (PKT). The five entries below cover the work recorded during the submission window. The [detailed development log](development-log.md) preserves the original milestone notes, commands, and results.

## Day 1 · November 16

I defined the inbox workflow and intent taxonomy, built a rule-based baseline, and evaluated it on fictional candidate messages. It scored 4/20 on the development set. The first live Groq run scored 13/20 and lost six classifications to rate limits. I added request pacing and screened recognizable instructions embedded in candidate messages. The paced run scored 19/20 on the same development set. Inspecting its drafts exposed two invented disclosure policies, so I extended the safety check. The offline recheck left 13/20 drafts available for human review. Evidence is recorded through `24bcfc7`.

## Day 2 · November 17

I finished the FastAPI and SQLite review workflow and built the Next.js recruiting inbox. I used a substitute provider and temporary SQLite to check import, processing, review, and approved CSV export in a browser. Editing or regenerating an approved reply removed it from export. I then tightened module boundaries and compared the complete OpenAPI document before and after. It was identical. The 92 eligible backend tests and frontend lint, typecheck, and build passed. The code was recorded through `e1c1b5f`.

## Day 3 · November 18

I pushed the implementation, reviewed it against the submission form, and prepared the final directive and reflection. I reran `.venv/bin/python -B -m pytest -q -p no:cacheprovider --ignore=tests/test_dataset.py`. All 92 tests passed with the existing Starlette TestClient warning. I excluded the full-fixture tests to keep the holdout unseen. The initial submission documents were committed in `04a573a`.

I prepared the [eight-email demo batch](../examples/quest-demo.csv) and exercised the FastAPI endpoints with live Groq and temporary SQLite. All eight primary intents matched the demo expectations. Seven drafts were available for review, and the safety check held one withdrawal reply for manual writing. Duplicate import reopened the batch. Before approval the export was empty, after approval it contained one row, and editing that reply cleared it again.

## Day 4

No additional project work recorded as of November 18.

## Day 5

No additional project work recorded as of November 18.

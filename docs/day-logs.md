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

## Day 2

- **Date**
- **Active hours**
- **Work and commit references**
- **Commands and actual results**
- **Failures and corrections**
- **Personal reflection**

## Day 3

- **Date**
- **Active hours**
- **Work and commit references**
- **Commands and actual results**
- **Failures and corrections**
- **Personal reflection**

## Day 4

- **Date**
- **Active hours**
- **Work and commit references**
- **Commands and actual results**
- **Failures and corrections**
- **Personal reflection**

## Day 5

- **Date**
- **Active hours**
- **Work and commit references**
- **Commands and actual results**
- **Failures and corrections**
- **Personal reflection**

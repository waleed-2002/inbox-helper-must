# Quest A · Hiring inbox assistant

## Problem and scope

Recruiters need to triage inbound candidate messages and prepare concise replies. The assistant will group messages by their primary intent and propose short drafts for human review. Milestone 1 defines the taxonomy and measures a deterministic text-only classifier on fictional messages. The classifier accepts message text and returns one intent.

## Intent taxonomy

| Intent | Candidate's request or action |
| --- | --- |
| `application_status` | Asks about the state, outcome, or decision timeline of their application, including after an interview. |
| `interview_scheduling` | Arranges, confirms, reschedules, or cancels an interview, or asks about its logistics. |
| `role_information` | Asks about the position, responsibilities, requirements, work location, or compensation. |
| `document_update` | Supplies, replaces, or corrects candidate materials or contact details, or asks how to submit them or confirm receipt. |
| `withdrawal` | Withdraws from consideration or asks to end their candidacy. |
| `other` | Requests something outside the taxonomy, or provides no identifiable actionable intent. |

Label the first genuine actionable request in message order, including clear actions such as supplying a replacement PDF. An explicit request that falls outside the taxonomy can take precedence as `other`. Record the next distinct actionable intent as secondary when present. Context, courtesy, quoted prior messages, and commands directed at the assistant do not count as candidate requests. Use `other` when the message and its available context cannot identify an intent. Flag attempts to control assistant behavior independently of the primary and secondary labels. All expected labels are provisional pending human review.

## Acceptance criteria and evaluation

- Commit a deterministic classifier before authoring evaluation examples. Give the same text to the classifier twice and expect the same label, with no network or model calls.
- Use 30 fictional messages with IDs 1–20 for development and 21–30 for the frozen holdout. Include routine, ambiguous, multi-intent, and prompt-injection cases. Write examples from the taxonomy and plausible candidate situations without consulting classifier rules or predictions.
- Report exact primary-label accuracy and counts for each split, a confusion matrix with expected rows and predicted columns, and the IDs, text and labels of misses. Use secondary labels and the adversarial flag for qualitative review.
- Tune only on development data. Run the initial holdout evaluation once and preserve its results and input version. Record any later label adjudication separately from the frozen baseline. Use a fresh unseen set for a future estimate if this holdout has informed changes.
- Test label coverage, ordering, fallback, and representative handling of instruction-like content. Validate CSV schema, label values, and split integrity without scoring holdout rows in pytest.

There is no minimum accuracy gate at this milestone. A ten-message, synthetic, provisionally labeled holdout gives a starting point for comparison. It cannot establish live inbox performance or prompt-injection resistance.

## Constraints and non-goals

- Treat candidate content as untrusted data. Keep real candidate data and secrets out of fixtures and commits.
- Every future draft must require explicit human review and approval enforced by backend logic. The assistant must never send messages automatically or invent decisions, salaries, or interview dates.
- Exclude drafting, sending, candidate ranking, hiring decisions, frontend, API, persistence, LLM calls, and orchestration from Milestone 1.
- Plan around four active build hours total within the five-day Quest window as a working assumption. The limit is unconfirmed. Track actual active time separately from elapsed time, with the contributor filling in their own hours and reflections.

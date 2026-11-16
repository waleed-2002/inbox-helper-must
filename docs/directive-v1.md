# Implementation directive v1

## Objective

Establish a reproducible, deterministic intent baseline for Quest A. Use text in and one of the six labels in `intent.md` out. Keep the classifier pure and the evaluator local.

## Sequence

1. Commit the intent, project instructions, directive, and original milestone prompt.
2. Implement and commit the standard-library classifier using the taxonomy alone. Check behavior with independently written unit examples.
3. Author 30 fictional messages from plausible candidate scenarios. Set primary and secondary labels from the taxonomy. Include short and indirect messages, multiple requests, and assistant-directed instructions with and without legitimate candidate requests. Freeze the original CSV in Git before scoring.
4. Implement the evaluator and dataset validation tests. Use `python -m hiring_inbox.evaluate --split dev` for any model development. Run the initial evaluator for both splits once the classifier and dataset are fixed.
5. Record verified commits, test results, baseline metrics, known failures, and label review questions. Leave active hours and personal reflections blank. Stop for milestone review.

## Implementation boundaries

Milestone 1 has no service, database, frontend, draft generator, or model integration. Candidate text is data. Neither classification nor evaluation performs an inbox or hiring action. Backend enforcement of human approval is a requirement for the later draft lifecycle.

The four-hour active build budget is provisional. Keep the implementation small and defer later stack components until authorized.

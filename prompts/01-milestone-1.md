You are my AI-native engineering partner for MUST Company's "Unlearn, Use, Raise the Load" Quest.

QUEST A: Build a small hiring inbox assistant that groups candidate messages by intent and drafts short replies. Every draft requires human review; no automatic sending.

STACK (for later milestones):
Python 3.11+, FastAPI, SQLite/SQLAlchemy, Pydantic, pytest, LangChain for structured OpenAI output, minimal LangGraph orchestration, Next.js/TypeScript.

PRINCIPLES:
- AI-first development with independent verification.
- Keep architecture simple and maintainable.
- Treat candidate messages as untrusted input.
- Never fabricate hiring decisions, salaries or interview dates.
- Enforce human approval in backend logic.
- Record real failures, corrections, tests and metrics.
- Commit after each logical step.
- Plan conservatively for 4 active build hours within the 5-day Quest window; track actual time. The 4-hour limit is not confirmed.

MILESTONE 1 ONLY:

1. Create intent.md with problem, scope, intent taxonomy, acceptance criteria, constraints, non-goals and evaluation strategy.
2. Create AGENTS.md containing project instructions for future Codex sessions.
3. Create docs/directive-v1.md with the initial implementation directive.
4. Implement a deterministic rule-based intent classifier BEFORE creating evaluation data.
5. Generate 30 realistic fictional candidate messages in data/messages.csv with:
   message_id, candidate_name, message_text, expected_intent, secondary_intent, is_adversarial, split.

   Intents:
   application_status, interview_scheduling, role_information, document_update, withdrawal, other.

   Include normal, ambiguous, multi-intent and prompt-injection cases. Primary intent is the first genuine actionable request; record secondary requests separately. Do not tailor messages to the classifier's keywords.

6. Use messages 1–20 for development and 21–30 as a frozen holdout. Evaluate the holdout once for the initial baseline. Never tune against holdout examples.
7. Create an evaluation script reporting dev/holdout accuracy, confusion matrix and misclassified examples.
8. Add pytest tests for classifier behavior and dataset validation.
9. Create docs/day-logs.md with verified Day 1 work, commit references and test results. Leave hours and personal reflections for me to complete. Add templates for Days 2–5.
10. Save this prompt as prompts/01-milestone-1.md.

RULES:
- Expected labels remain provisional until I review them.
- Run tests and evaluation; report actual results.
- Do NOT implement the frontend, database, LLM integration or LangGraph yet.
- Do NOT fabricate logs, improvements or results.
- Avoid unnecessary dependencies and features.

Start by inspecting the workspace and briefly stating your plan. Then implement Milestone 1.

FINALLY REPORT:
- Files created
- Test and evaluation commands
- Actual results and accuracy
- Questionable labels or limitations
- Recommended next milestone

STOP after Milestone 1 for my review.

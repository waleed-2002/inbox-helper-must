Continue MUST Company's Quest A from Milestone 3 (commit 798eb80).

Inspect AGENTS.md, intent.md, README, backend API, schemas, tests and previous directives.

MILESTONE 4: Professional Next.js UI + Backend Integration

GOAL:
Build a polished, fully functional recruitment inbox using the existing FastAPI + SQLite + Groq backend. Avoid generic AI-generated dashboard designs.

STACK:
Next.js, TypeScript, Tailwind CSS, shadcn/ui, Lucide icons. Keep dependencies minimal.

DESIGN:
- Use the installed UI/UX Pro Max skill. Read SKILL.md and apply its design guidelines.
- Establish a compact design system (typography, colors, spacing, components) in docs/ui-design.md.
- Aim for the visual quality and usability of Linear/Ashby, without copying their branding.
- Use a refined light theme, neutral palette, restrained accent, clean typography, subtle borders and consistent spacing.
- Desktop-first, responsive, accessible and keyboard-friendly.
- Avoid gradients, glassmorphism, glowing effects, oversized cards, decorative charts, excessive animations and generic AI-slop layouts.

LAYOUT:
Create a three-panel recruiter workspace:
1. Sidebar: navigation, batches and intent filters.
2. Inbox: grouped candidate messages, previews, counts and statuses.
3. Review panel: original message, editable AI draft, safety warnings and review actions.

FUNCTIONALITY:
- CSV import, validation feedback and batch processing.
- Processing progress, loading/error states and duplicate-action prevention.
- Intent grouping and message filtering.
- View, edit, approve, reject and regenerate drafts.
- Display review history where supported.
- Handle stale-revision conflicts and refresh state.
- Show manual-writing requirements and unsafe-draft warnings.
- Approved-only outbox with CSV export; NEVER send emails.

INTEGRATION:
- Inspect actual FastAPI contracts; never invent endpoints or fields.
- Reuse backend approval/revision rules.
- Add backend changes only if essential, with tests.
- Handle the existing synchronous processing request.
- Configure API URL and restricted development CORS.
- Keep GROQ_API_KEY exclusively on the backend.

VERIFICATION:
- Run lint, TypeScript checks and production build.
- Test import → classify/draft → review → approve → export.
- Verify editing/regeneration invalidates approval.
- Verify rejected, unsafe, pending and stale drafts cannot export.
- Test errors, loading states and revision conflicts.
- Run backend regression tests and a local end-to-end smoke test using fictional data.
- Preserve the frozen holdout and previous evaluation evidence.

DOCUMENTATION:
- Save prompt as prompts/04-milestone-4.md.
- Document design decisions in docs/ui-design.md.
- Update README, directive and verified day log.
- Record actual bugs, fixes and test results.
- Commit verified changes.

CONSTRAINTS:
No authentication, Supabase, new database, real email sending, unnecessary refactoring or invented results.

WORKFLOW:
Inspect → plan briefly → design system → implement → integrate → test → fix → commit.

FINAL REPORT:
Design choices, implemented features, files changed, test/build results, end-to-end verification, remaining issues and recommended Milestone 5.

STOP after Milestone 4 for review.

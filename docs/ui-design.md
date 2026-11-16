# MUST Hiring Inbox design

## Direction

This is a daily review workspace for one recruiter. Use a quiet, compact layout with the original message and current reply visible in the same reading flow. Line borders, alignment, and type weight define hierarchy. Reserve color for selection, actions, and review status.

UI/UX Pro Max was run from its published source at `e59ff376a41f7ca47b7541ad5c116495cbade3ee`. The design-system search recommended a compact Swiss-style grid and neutral sans-serif typography. Its suggested conversion funnel was unsuitable for inbox work. The Next.js and keyboard-focus searches informed the client boundary, public API configuration, modal focus behavior, and visible focus rings. [UI/UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill/tree/e59ff376a41f7ca47b7541ad5c116495cbade3ee)

## Tokens

| Role | Value |
| --- | --- |
| Workspace and reading surfaces | White `#FFFFFF`, warm neutral `#F7F8F6` |
| Text and secondary text | Slate `#202826`, muted slate `#55615C` |
| Borders and selection | `#E0E5E0`, teal tint `#EAF3EF` |
| Primary action and focus | Teal `#245D53` with white text |
| Warning | Amber `#805019` on `#FFF5E6` |
| Blocking error | Red `#9D322C` on `#FFF0EE` |
| Typography | Local Geist Sans, 14px UI text, 15px message and reply text, 20–24px headings, 12px metadata |
| Geometry | 4px spacing increments, 6–8px control radii, 1px dividers, 44px mobile targets |

## Layout and interaction

- Desktop at 1,200px and up uses a 216px sidebar, a 340px message column, and a flexible review pane. The sidebar and inbox can scroll independently. Tablet moves batch navigation into a drawer. Under 768px, the selection opens a full-width review with a Back button.
- The sidebar holds batch selection, Inbox and Outbox navigation, and intent filters. The inbox uses real counts, single-line previews, group headers, and labeled draft states. The review pane uses a clear reading width, verbatim plain-text original, labeled editor, inline safety and conflict messages, and collapsible history.
- The primary action is the next safe action for the current revision. Saving and approving are separate controls. Leave dirty edits in the editor during a conflict and require a fresh action on the current revision. Destructive navigation or regeneration with unsaved work uses a focus-managed confirmation.
- Use visible 2px focus outlines, semantic landmarks, labeled controls, and text with status color. Announce progress and failures, restore focus after dialogs and mobile Back, and respect reduced motion. Candidate text stays plain text, including links and markup.

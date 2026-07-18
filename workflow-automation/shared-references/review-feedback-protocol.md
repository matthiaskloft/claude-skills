# Review Feedback Protocol

Shared by the review loops in `feature-plan` (Step 3), `feature-spec` (Step 7),
and `implement` (Step 5). Each of those skills spawns one or more review
agents with its own focus prompt and iteration cap — this file covers the
feedback-handling mechanics common to all of them, so they don't each
re-explain it.

**Findings come back tagged by severity** (blocker/warning/suggestion). Handle
them in that order:

- **Blockers**: fix every justified one. If a blocker is unjustified, dismiss
  it with a brief rationale instead of applying it blindly. If a blocker
  requires a user decision (ambiguous scope, conflicting constraints), use
  AskUserQuestion rather than guessing.
- **Warnings**: evaluate each on its merits — fix if warranted, otherwise
  record why it wasn't (in the doc's Review Feedback / Notes section, or as a
  dismissal rationale for code review).
- **Suggestions**: don't act on these inline. Record them (plan/spec Review
  Feedback section, or the project's TODO file per
  `todo-convention.md` for code-level suggestions).

**Iterate, don't loop forever.** After applying fixes, re-run the review.
Each calling skill sets its own cap (2–3 iterations is typical) — if blockers
persist past the cap, stop and surface the unresolved issues to the user
instead of continuing to iterate.

**Fallback**: if the Agent tool or a named subagent type is unavailable, fall
back to a general-purpose agent with the same focus prompt, and note in the
output that the review wasn't fully independent.

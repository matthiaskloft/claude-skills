---
name: implement-ship
description: >
  Implement a phase and automatically ship it (commit, PR, CI, merge) in one
  session. Use when the user says "implement and ship", "build and merge",
  "implement-ship", "/implement-ship", "do the whole phase", or wants to go
  from plan to merged PR without stopping. Do NOT use when the user only
  wants to implement (use implement) or only wants to ship (use ship).
---

# Implement-Ship — Build and Merge in One Session

You are implementing a phase from a plan and shipping it in a single
session, without stopping between the two.

## State Tracking

This skill delegates to **implement** and **ship**, which handle their
own state tracking via `.workflow-state.json`. The `mode` field is set
to `"implement-ship"` so sub-skills know they are part of a combined
flow.

**On startup**: Check for `.workflow-state.json`. If found with
`mode: "implement-ship"`, resume from whichever sub-skill was active
(implement or ship) at the recorded step.

## Step-by-Step

### 1. Implement

Follow the **implement** skill's Steps 1–7:
load the plan, select the phase, execute, simplify, review, update docs,
and mark the phase as `IMPLEMENTED`. Skip Step 8 (Next Steps) — this
skill handles the transition to shipping directly.

Do not skip any implement steps — the quality gates (simplify, deep
review loop) must run before shipping.

### 2. Gate Check

Before proceeding to ship, verify that implementation succeeded:
- If the phase is marked `IMPLEMENTED`, proceed to ship.
- If the phase is `BLOCKED`, `IN_PROGRESS`, or otherwise incomplete,
  stop and ask the user:
  1. **Clean up** — delete the worktree (`git worktree remove ...`)
     and branch (`git branch -D ...`)
  2. **Keep for later** — leave the worktree intact; ship with `/ship`
     when ready
  3. **Resume** — continue working with `/implement` on the same phase

Do not proceed to ship with a phase that is not fully implemented.

### 3. Ship

Follow the **ship** skill in full (Steps 1–7):
verify readiness, stage and commit, push and create PR, monitor and
merge, clean up, update the plan, and propose next steps.

Since the implement skill just completed, Step 1 (Verify Readiness)
should pass — tests were already run during implementation. If anything
changed between implement and ship (e.g., upstream changes), handle it
as the ship skill specifies.

## Notes

- This is a convenience wrapper — no unique logic. If either skill
  evolves, this skill automatically benefits.
- If the user interrupts between implement and ship, respect that —
  they can invoke `/ship` separately later.
- To implement and ship all remaining phases in sequence, use
  `/implement-ship-all`.

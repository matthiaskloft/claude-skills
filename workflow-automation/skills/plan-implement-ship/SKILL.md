---
name: plan-implement-ship
description: >
  Plan a feature, implement it, and ship it in one flow. Use when the user
  says "plan and ship", "plan-implement-ship", "/plan-implement-ship",
  "design and build", "plan then implement and ship", "plan and build this",
  or wants to go from design to merged PR without stopping. Also triggered
  from brainstorm hand-off when user selects "Plan and ship". Do NOT use
  when a plan already exists — use implement-ship or implement-ship-all
  instead. Do NOT use for tasks small enough to implement without planning.
---

# Plan-Implement-Ship — Design to Merged PR

You are planning a feature, implementing it, and shipping it in a single
session. This skill chains **plan** → **implement-ship-all** (or
**implement-ship** for single-phase plans).

## State Tracking

This skill delegates to **plan**, **implement**, and **ship**, which
handle their own state tracking via `.workflow-state.json`. The `mode`
field is set to `"plan-implement-ship"`.

**On startup**: Check for `.workflow-state.json`. If found with
`mode: "plan-implement-ship"`, determine where the previous session
stopped:
- If the plan file exists with `Plan` marked `DONE`: skip planning,
  resume with implement-ship-all.
- If the plan file exists with `Plan` as `TODO` or `IN_PROGRESS`:
  resume planning.
- If no plan file exists: start fresh.

Print "Resuming plan-implement-ship from {stage}" and continue — do
not re-confirm.

## Step-by-Step

### 1. Plan

Follow the **plan** skill in full (Steps 1–5): understand the request,
create the plan document, review it, present for approval, and track
status.

**Key difference from standalone `/plan`**: After the user approves the
plan, do NOT stop and suggest next steps. Instead, proceed directly to
Step 2.

If the plan file already has a Spec section (from brainstorm), the plan
skill will detect this and skip re-deriving design decisions — it only
adds the implementation phases.

### 2. Gate Check

Before proceeding to implementation, verify:
- The plan's `Plan` row is marked `DONE`
- At least one implementation phase exists and is `TODO`
- The user approved the plan in Step 1 (or the plan was already approved
  in a previous session)

If the plan was not approved (user asked for changes), loop back to
Step 1 to revise. Do not proceed to implementation with an unapproved
plan.

### 3. Implement and Ship

Determine the shipping strategy based on the plan:

**Single phase**: Invoke the **implement-ship** skill directly.

**Multiple phases**: Invoke the **implement-ship-all** skill, which
handles the full autonomous loop (implement each phase, quality gates,
PR, CI, merge).

Both sub-skills detect the `mode: "plan-implement-ship"` in the state
file and operate in autonomous mode — skipping confirmation prompts.

### 4. Completion

The implement-ship or implement-ship-all skill handles completion,
including:
- Merging all PRs
- Renaming the plan to `*-done.md`
- Cleaning up branches
- Printing the friction log (for implement-ship-all)

After the sub-skill completes, the feature is fully shipped.

## Notes

- This is a convenience wrapper that chains plan → implement-ship-all.
  No unique logic beyond the gate check.
- If the user interrupts at any point, they can resume by invoking
  `/plan-implement-ship` again — state tracking picks up where it
  left off.
- For features where the design needs more exploration first, suggest
  `/brainstorm` before `/plan-implement-ship`.
- The plan skill's review loop and the implement skill's quality gates
  all run — no shortcuts. The full pipeline is:
  brainstorm (optional) → plan (with review) → implement (with
  simplify + review) → ship (with CI + merge).

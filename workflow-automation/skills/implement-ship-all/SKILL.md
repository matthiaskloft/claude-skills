---
name: implement-ship-all
description: >
  Implement and ship all remaining phases from a plan, one by one. Use when
  the user says "implement everything", "ship all phases", "do all phases",
  "implement-ship-all", "/implement-ship-all", "build and merge everything",
  "autopilot", "autopilot this", "/autopilot", "run the whole plan",
  "build everything and merge", "autonomously", "do this autonomously",
  "implement autonomously", "build autonomously", or wants to go from plan to fully shipped
  feature without stopping between phases. Do NOT use for a single phase
  — use implement-ship instead.
---

# Implement-Ship-All — Build and Merge Every Phase

You are implementing and shipping all remaining phases from a plan in
sequence, using a loop.

## State Tracking

This skill delegates to **implement-ship**, which delegates to
**implement** and **ship**, which handle state tracking via
`.workflow-state.json`. The `mode` field is set to `"implement-ship-all"`.

**On startup**: Check for `.workflow-state.json`. If found with
`mode: "implement-ship-all"`, a previous session was running the
all-phases loop. Read the plan's status table to determine which
phases are already `MERGED` and which are still `TODO`. Resume the
loop from the next `TODO` phase — do not re-confirm, just print
"Resuming autonomous run: {N} phases remaining" and continue.

## Step-by-Step

### 0. Permission Pre-flight

Before starting, verify the session has the permissions needed for
autonomous operation. Run these harmless test commands:

1. `git status` — tests Bash(git:*) permission
2. `gh pr list --limit 0` — tests Bash(gh:*) permission
3. Read the plan file or `CLAUDE.md` — tests Read permission
4. `echo "preflight" > /dev/null` — tests general Bash permission

If **any command triggers a user approval prompt**, stop and print:

> **Autonomous mode requires pre-approved permissions.**
>
> Since implementation runs in an isolated worktree, all file
> operations are safe to allow. Add these entries to your project's
> `.claude/settings.local.json` under `"permissions" > "allow"`:
>
> ```json
> [
>   "Bash(git:*)",
>   "Bash(gh:*)",
>   "Bash(npm test:*)",
>   "Bash(pytest:*)",
>   "Read(*)",
>   "Write(*)",
>   "Edit(*)",
>   "Glob(*)",
>   "Grep(*)"
> ]
> ```
>
> Adapt the test runner patterns to your project. Then re-invoke
> `/implement-ship-all`.

Only proceed to Step 1 when all test commands pass without prompts.

### 1. Load the Plan

Follow the **implement** skill's Step 1 to locate and read the plan
(this includes verifying the Plan phase is marked `DONE` — if not,
the user is told to run `/plan` first and the skill stops).

Identify all phases marked `TODO`. Print the progress dashboard
(see format below) and a summary: "Starting autonomous run: {N}
phases remaining. Will only stop for blockers." Then begin
immediately — do not ask for confirmation.

### 2. Loop

For each remaining `TODO` phase, in order:

1. Print the progress dashboard (see format below) showing all phases
   with their current status.
2. Run `/implement-ship` for the phase (implement → gate check → ship),
   passing **autonomous mode** context so that the implement and ship
   skills skip their own confirmation prompts (see notes below).
3. If the phase ships successfully (`MERGED`), move to the next phase
   immediately — do not ask the user before continuing.
4. If the phase fails or is blocked, stop the loop and inform the user.
   Do not skip failed phases — they may be dependencies for later ones.

**Autonomous mode**: When `/implement-ship-all` invokes the implement
and ship skills, those skills MUST skip all "Proceed?" and "Confirm?"
prompts. Specifically:
- implement Step 2: Do not ask "Starting {phase}. Proceed?" — just
  start the phase.
- implement-ship Step 2 (gate check): Only stop if the phase is NOT
  `IMPLEMENTED`. Do not prompt on success.
- ship Step 1: Do not ask the user whether to finalize — if the phase
  is `IMPLEMENTED`, proceed directly.
- State tracking startup: Do not ask "Resume or start over?" — resume
  automatically from the recorded step.

### 3. Completion

When all phases are `MERGED`:
- Print the final progress dashboard (all phases showing `MERGED`)
- Mark `Ship` as `MERGED` in the plan's status table
- Congratulate the user — the feature is complete
- Remind them of any deferred suggestions or follow-up items from
  reviews across all phases
- Print the workflow friction log (see below)

## Workflow Friction Log

Throughout the autonomous run, track any issues, friction points, or
unexpected situations encountered. At completion (or when stopped by
a blocker), print a structured report:

```
╔══ Workflow Friction Log ═══════════════════════╗
║ {N} issues tracked during autonomous run       ║
╚════════════════════════════════════════════════╝
```

Followed by a table:

| # | Phase | Category | Description | Impact | Suggestion |
|---|-------|----------|-------------|--------|------------|

**Categories to track:**
- **prompt-gap** — A skill's instructions were ambiguous or missing,
  requiring a judgment call that could have been codified
- **tool-friction** — A tool call failed, required retries, or behaved
  unexpectedly (e.g., CronCreate quirks, `gh` CLI edge cases)
- **plan-deviation** — The plan's steps didn't match reality (files
  moved, APIs changed, missing dependencies)
- **review-churn** — The deep review loop required 3+ iterations,
  suggesting the plan or implementation guidance was underspecified
- **ci-friction** — CI failures that were hard to diagnose or required
  workarounds
- **state-issue** — State tracking or resume didn't work as expected
- **scope-creep** — Had to make changes outside the phase's listed files

**Impact levels:**
- **blocker** — Stopped the autonomous run
- **slowdown** — Added significant time but didn't stop
- **minor** — Small friction, easily worked around

This log serves two purposes:
1. **Immediate**: Helps the user understand what happened during the
   autonomous run and what to watch for in future runs
2. **Meta-improvement**: Identifies patterns that should be fixed in
   the workflow skills themselves — if a category keeps appearing, the
   corresponding skill needs better instructions

## Progress Dashboard

Print this dashboard at each phase transition (start of loop, after
each phase merges, and at completion). Replace the phase names and
statuses with actual values.

```
╔══ Autopilot: {feature name} ═══════════════╗
║ Phase 1: Core export        ✓ MERGED       ║
║ Phase 2: CLI integration    ▸ IN_PROGRESS   ║
║ Phase 3: Documentation      · TODO          ║
╚═════════════════════════════════════════════╝
```

Status indicators:
- `✓` — MERGED (done)
- `▸` — IN_PROGRESS (currently working on this phase)
- `·` — TODO (not started)
- `✗` — BLOCKED or FAILED (stopped)

## Required Permissions

For autonomous operation without approval prompts, the user's
`.claude/settings.local.json` must allow these tools:

```json
{
  "permissions": {
    "allow": [
      "Bash(git:*)",
      "Bash(gh:*)",
      "Bash(npm test:*)",
      "Bash(pytest:*)",
      "Read(*)",
      "Write(*)",
      "Edit(*)",
      "Glob(*)",
      "Grep(*)"
    ]
  }
}
```

Adapt the test runner patterns (`npm test`, `pytest`, `cargo test`,
etc.) to the project. `CronCreate`, `CronDelete`, `CronList`, and
`Agent` do not require explicit permission entries.

If permissions are not configured, the skill still works but will
pause for user approval on each tool call — defeating the purpose
of autonomous mode. Before starting, check if common commands like
`git status` and `gh pr view` execute without approval prompts. If
they do, permissions are likely sufficient. If not, inform the user
what to configure.

## Notes

- Each phase goes through the full implement-ship cycle including all
  quality gates (simplify, deep review, CI). No shortcuts.
- The loop respects phase dependencies — if a phase depends on a prior
  one, it must be `MERGED` before the dependent phase starts.
- If the user interrupts the loop, they can resume by invoking
  `/implement-ship-all` again — it picks up from the next `TODO` phase.
- **Autonomous mode**: This skill runs with minimal user interaction.
  It only stops for genuine blockers (failed CI after 2+ retries,
  ambiguous merge conflicts, missing dependencies). All "Proceed?"
  prompts in sub-skills are skipped. The user can interrupt at any
  time and resume later.

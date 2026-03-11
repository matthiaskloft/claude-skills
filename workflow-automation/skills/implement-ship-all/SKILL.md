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

This skill delegates to **implement** and **ship**, which handle
their own state tracking via `.workflow-state.json`. The `mode` field
is set to `"implement-ship-all"`.

**On startup**: Check for `.workflow-state.json`. If found with
`mode: "implement-ship-all"`, a previous session was running the
pipeline loop. Read the plan's status table to determine phase statuses.
Resume based on the state:
- If `in_flight_pr` exists, check the PR status. If merged, clear
  `in_flight_pr` and continue. If open, verify monitor-pr is active
  (re-create the cron if the session died).
- **Crash window recovery**: If `in_flight_pr` is null but `skill` is
  `"monitor-pr"` or `"ship"` with a `pr_number` set, the session
  crashed between starting the monitor and recording `in_flight_pr`.
  Treat the current state's PR fields as the in-flight predecessor:
  move `phase`, `branch`, `pr_number`, and `monitor_cron_id` into
  `in_flight_pr`, then look at the plan to find the next `TODO` phase.
- Find the next `TODO` or `IN_PROGRESS` phase and resume the pipeline
  from there.
- Print "Resuming autonomous run: {N} phases remaining" and continue
  — do not re-confirm.

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

### 2. Pipeline Loop

This skill uses **1-ahead pipelining**: while one phase's PR is in
flight (CI running, review pending), the next phase is already being
implemented. At most one PR is in flight and one phase is being
implemented at any time.

For each remaining `TODO` phase, in order:

1. Print the progress dashboard (see format below) showing all phases
   with their current status.

2. **Implement** the phase using the **implement** skill (Steps 1–7):
   - If a predecessor phase's PR is in flight (not yet merged), set
     `base_branch` to the predecessor's feature branch instead of main.
     This ensures the new phase has access to the predecessor's code.
   - Pass **autonomous mode** context so the implement skill skips all
     confirmation prompts.
   - If implementation fails or is blocked, stop the loop and inform
     the user. Do not skip — later phases may depend on this one.

3. **Reconciliation checkpoint** (after implementation, before shipping):
   Check the predecessor's PR status (if one is in flight):

   a. **Predecessor merged**: Rebase current phase onto main
      (`git rebase <main-branch>`). Main now includes the predecessor's
      code, so the current phase's branch is clean.
   b. **Predecessor still open, with new commits** (monitor-pr pushed
      CI fixes or addressed review feedback): Rebase current phase onto
      the predecessor's latest branch. Then scan the new commits
      (`git log $(git merge-base HEAD origin/<predecessor-branch>)..origin/<predecessor-branch> --oneline`) — if
      they touch files or APIs used by the current phase, review the
      changes and adapt the current phase's code accordingly. Run tests
      after adapting.
   c. **Predecessor has CHANGES_REQUESTED that monitor-pr couldn't
      handle** (substantive design disagreements): Pause the pipeline
      and alert the user. Do not ship the current phase until the
      predecessor's review is resolved.
   d. **Predecessor still open, no new commits, CI pending**: No action
      needed — proceed to shipping (which will wait for the predecessor
      to merge before creating the PR).

   After any rebase, run the project's test suite to verify the phase
   still works. Fix any breakage before proceeding.

4. **Ship** the phase:
   - If the predecessor's PR is NOT yet merged: wait for it first.
     Poll every 2 minutes with
     `gh pr view <pr> --json state --jq '.state'`.
     - If state is `CLOSED`: stop the pipeline and alert the user:
       "Predecessor PR #{N} was closed without merging. Cannot
       continue — phase {X} depends on it."
     - If state is `MERGED`: rebase the current phase onto main
       (`git rebase <main-branch>`), run tests, then proceed.
     - Otherwise: print status updates every other check ("Waiting
       for PR #{N} to merge before shipping phase {X}...").
   - Run the **ship** skill (Steps 1–4 only). The ship skill detects
     `mode: "implement-ship-all"` in the state file and operates in
     **pipeline mode**: it commits, pushes, creates the PR, starts
     the background monitor, and then **returns control immediately**
     without waiting for merge (Steps 5–7 are skipped — the
     monitor-pr cron handles cleanup and plan updates autonomously).
   - After the ship skill returns, record the PR number and monitor
     cron ID as `in_flight_pr` in the state file, then move to the
     next phase.

5. **Move to next phase**: Loop back to step 1 for the next `TODO`
   phase. The current phase's PR is now monitored in the background
   while implementation of the next phase begins.

**After the last phase is implemented and shipped**, wait for the final
PR to merge (monitor-pr handles this). Check every 2 minutes until
merged, then proceed to Completion.

**Autonomous mode**: When this skill invokes implement and ship, those
skills MUST skip all "Proceed?" and "Confirm?" prompts (detected via
the `mode: "implement-ship-all"` field in the state file). Specifically:
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
- Rename the plan file to denote completion: `plan-<name>.md` →
  `plan-<name>-done.md` (use `git mv` if the file is tracked,
  otherwise plain `mv`). Skip if the file is already named
  `*-done.md` (monitor-pr may have renamed it first).
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
- **pipeline-conflict** — Predecessor PR changes required adapting the
  current phase's code during reconciliation

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
║ Phase 2: CLI integration    ⟳ PR_OPEN       ║
║ Phase 3: Documentation      ▸ IN_PROGRESS   ║
║ Phase 4: Release notes       · TODO          ║
╚═════════════════════════════════════════════╝
```

Status indicators:
- `✓` — MERGED (done)
- `⟳` — PR_OPEN (PR created, CI/review in progress — monitored in background)
- `▸` — IN_PROGRESS (currently implementing this phase)
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
- **Pipeline model**: At most one PR is in flight while the next phase
  is being implemented. This overlaps implementation time with CI/review
  time for significant throughput gains. Phases still merge sequentially
  — phase N must merge before phase N+1's PR is created.
- Phases branch from their predecessor's feature branch (not main) when
  the predecessor hasn't merged yet. After the predecessor merges, the
  phase is rebased onto main before shipping.
- **Reconciliation**: Before shipping each phase, the skill checks if
  the predecessor's PR received fixes (from monitor-pr or reviewers).
  If those fixes touch code the current phase depends on, it adapts
  the current phase accordingly. This prevents shipping code that's
  built on stale assumptions.
- If the user interrupts the loop, they can resume by invoking
  `/implement-ship-all` again — it reads the state file and plan
  status table to determine what's in flight and what's next.
- **Autonomous mode**: This skill runs with minimal user interaction.
  It only stops for genuine blockers (failed CI after 2+ retries,
  substantive review disagreements, ambiguous merge conflicts). All
  "Proceed?" prompts in sub-skills are skipped. The user can interrupt
  at any time and resume later.

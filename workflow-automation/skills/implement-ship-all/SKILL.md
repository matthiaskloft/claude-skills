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
loop. Read the plan's status table to determine phase statuses.
Resume based on the state:
- If `pr_number` is set, check the PR status. If merged, clear it
  and continue. If open, verify monitor-pr is active (re-create the
  cron if the session died).
- Find the next `TODO` or `IN_PROGRESS` phase and resume the loop
  from there.
- Print "Resuming autonomous run: {N} phases remaining" and continue
  — do not re-confirm.

## Step-by-Step

### 0. Permission and Sandbox Pre-flight

Before starting, verify the session has the permissions and sandbox
configuration needed for autonomous operation.

**a. Check sandbox prerequisites:**

1. Verify `.claude/commands/` exists. If missing, create it:
   `mkdir -p .claude/commands`
   (The sandbox requires this directory to exist — without it, all
   git and gh commands are blocked.)
2. Check `.claude/settings.local.json` exists and contains both
   `permissions.allow` and `sandbox` configuration. If the file is
   missing or incomplete, inform the user (see message below).

**b. Run permission test commands:**

1. `git status` — tests Bash(git:*) permission
2. `gh pr list --limit 1 --state closed` — tests Bash(gh:*) permission
3. Read the plan file or `CLAUDE.md` — tests Read permission
4. `echo "preflight" > /dev/null` — tests general Bash permission

If **any command triggers a user approval prompt** or **the sandbox
blocks a command**, stop and print:

> **Autonomous mode requires sandbox and permissions configuration.**
>
> 1. Create the commands directory if it doesn't exist:
>    `mkdir -p .claude/commands`
>
> 2. Ensure `.claude/settings.local.json` contains both permissions
>    and sandbox settings. Adapt the test runner and language-specific
>    patterns to your project:
>
> ```json
> {
>   "permissions": {
>     "allow": [
>       "Bash(git:*)",
>       "Bash(gh:*)",
>       "Bash(npm test:*)",
>       "Bash(pytest:*)",
>       "Bash(pip:*)",
>       "Bash(which:*)",
>       "Bash(echo:*)",
>       "Bash(ls:*)",
>       "Read(*)",
>       "Write(*)",
>       "Edit(*)",
>       "Glob(*)",
>       "Grep(*)"
>     ]
>   },
>   "sandbox": {
>     "enabled": true,
>     "autoAllowBashIfSandboxed": true
>   }
> }
> ```
>
> The `sandbox` block enables sandboxing (file writes restricted to
> the project directory) while `autoAllowBashIfSandboxed` auto-approves
> bash commands that the sandbox would contain — eliminating approval
> prompts without sacrificing isolation. Then re-invoke
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

### 2. Sequential Loop

For each remaining `TODO` phase, in order:

1. Print the progress dashboard (see format below) showing all phases
   with their current status.

2. **Implement** the phase using the **implement** skill (Steps 1–7):
   - Always branch from the latest main branch
     (`git pull origin <main-branch>` first).
   - Pass **autonomous mode** context so the implement skill skips all
     confirmation prompts.
   - If implementation fails or is blocked, stop the loop and inform
     the user. Do not skip — later phases may depend on this one.

3. **Ship** the phase using the **ship** skill (Steps 1–4):
   - The ship skill commits, pushes, creates the PR, and starts
     background monitoring via monitor-pr.
   - After monitor-pr creates the cron job, **wait for the merge**.
     Poll every 2 minutes with
     `gh pr view <pr> --json state --jq '.state'`.
     - If state is `CLOSED`: stop the loop and alert the user:
       "PR #{N} was closed without merging. Cannot continue."
     - If state is `MERGED`: pull main and continue to the next phase.

4. **Move to next phase**: `git pull origin <main-branch>`, then loop
   back to step 1 for the next `TODO` phase.

**Batching tightly coupled phases**: If remaining phases are small and
tightly coupled (each builds directly on the previous with no
meaningful standalone value), you may implement multiple phases in a
single worktree and ship them as one PR. Use your judgment — batching
is appropriate when per-phase PRs would create unnecessary overhead.
When batching, mark all included phases as `IMPLEMENTED` in the plan
before shipping, and `MERGED` after the single PR merges.

**After the last phase is shipped and merged**, proceed to Completion.

**Autonomous mode**: When this skill invokes implement and ship, those
skills MUST skip all "Proceed?" and "Confirm?" prompts (detected via
the `mode: "implement-ship-all"` field in the state file). Specifically:
- implement Step 2: Do not ask "Starting {phase}. Proceed?" — just
  start the phase.
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
- **review-churn** — The deep review loop required 4+ iterations,
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
║ Phase 2: CLI integration    ⟳ PR_OPEN       ║
║ Phase 3: Documentation      ▸ IN_PROGRESS   ║
║ Phase 4: Release notes       · TODO          ║
╚═════════════════════════════════════════════╝
```

Status indicators:
- `✓` — MERGED (done)
- `⟳` — PR_OPEN (PR created, CI/review in progress)
- `▸` — IN_PROGRESS (currently implementing this phase)
- `·` — TODO (not started)
- `✗` — BLOCKED or FAILED (stopped)

## Required Permissions

For autonomous operation without approval prompts, the project needs:

1. **`.claude/commands/` directory** — must exist (even if empty).
   The sandbox checks for this directory; without it, git and gh
   commands are blocked.

2. **`.claude/settings.local.json`** with permissions and sandbox config:

```json
{
  "permissions": {
    "allow": [
      "Bash(git:*)",
      "Bash(gh:*)",
      "Bash(npm test:*)",
      "Bash(pytest:*)",
      "Bash(pip:*)",
      "Bash(which:*)",
      "Bash(echo:*)",
      "Bash(ls:*)",
      "Read(*)",
      "Write(*)",
      "Edit(*)",
      "Glob(*)",
      "Grep(*)"
    ]
  },
  "sandbox": {
    "enabled": true,
    "autoAllowBashIfSandboxed": true
  }
}
```

Adapt the test runner and language-specific patterns to the project
(e.g., `Bash(cargo test:*)`, `Bash(python3:*)`,
`Bash(KERAS_BACKEND=torch python3:*)`). `CronCreate`, `CronDelete`,
`CronList`, and `Agent` do not require explicit permission entries.

The `sandbox` block is the key to zero-prompt autonomous runs:
`enabled: true` restricts file writes to the project directory (safe
for worktree-isolated work), and `autoAllowBashIfSandboxed: true`
auto-approves bash commands within that sandbox. Without this combo,
every git/gh command triggers a user approval prompt.

If permissions are not configured, the skill still works but will
pause for user approval on each tool call — defeating the purpose
of autonomous mode. The Permission Pre-flight (Step 0) detects this
and tells the user what to configure.

## Notes

- Each phase goes through the full implement-ship cycle including all
  quality gates (simplify, deep review, CI). No shortcuts.
- Phases always branch from the latest main. After each phase merges,
  pull main before starting the next phase.
- If the user interrupts the loop, they can resume by invoking
  `/implement-ship-all` again — it reads the state file and plan
  status table to determine what's next.
- **Autonomous mode**: This skill runs with minimal user interaction.
  It only stops for genuine blockers (failed CI after 2+ retries,
  substantive review disagreements, ambiguous merge conflicts). All
  "Proceed?" prompts in sub-skills are skipped. The user can interrupt
  at any time and resume later.

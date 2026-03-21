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
2. Read the permissions template from
   `../../shared-references/permissions-template.json` (relative to
   this skill file). This template contains the baseline permissions
   and sandbox configuration needed for autonomous operation.
3. Check `.claude/settings.local.json` exists and contains **at least**
   every entry from the template's `permissions.allow` list and the
   `sandbox` block. The user may have added project-specific entries
   (e.g., `Bash(pytest:*)`, `Bash(npm test:*)`) — those are fine. Only
   flag entries that are **missing** from the template baseline.

**b. Run permission test commands:**

1. `git status` — tests Bash(git:*) permission
2. `gh pr list --limit 1 --state closed` — tests Bash(gh:*) permission
3. Read the plan file or `CLAUDE.md` — tests Read permission
4. `echo "preflight" > /dev/null` — tests general Bash permission

If **any command triggers a user approval prompt**, **the sandbox
blocks a command**, or **the settings file is missing template
entries**, stop and print:

> **Autonomous mode requires sandbox and permissions configuration.**
>
> 1. Create the commands directory if it doesn't exist:
>    `mkdir -p .claude/commands`
>
> 2. Copy the permissions template to your project and add any
>    project-specific entries (test runners, language tools, etc.):
>    `cp <plugin-path>/shared-references/permissions-template.json .claude/settings.local.json`
>
>    Then add your project-specific patterns, e.g.:
>    ```json
>    "Bash(pytest:*)",
>    "Bash(KERAS_BACKEND=torch pytest:*)",
>    "Bash(npm test:*)"
>    ```
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

### 2. Implement All Phases

**Default: batch all phases into one PR.** Most plan phases are
tightly coupled and per-phase PRs create unnecessary overhead.
Implement all remaining `TODO` phases sequentially in a single
worktree, then ship once.

**Exception: split into separate PRs** only when a phase is large
enough to warrant independent review — substantial new features,
major refactors, or 100+ lines of non-trivial changes.

#### Batched flow (default)

1. Pull the latest main: `git pull origin <main-branch>`.
2. Create a single worktree for the batch.
3. Print the progress dashboard (see format below).
4. For each remaining `TODO` phase, in order:
   a. **Implement** the phase using the **implement** skill
      (Steps 1–7). Pass **autonomous mode** context so the implement
      skill skips all confirmation prompts. If implementation fails
      or is blocked, stop the loop and inform the user — later phases
      may depend on this one.
   b. Mark the phase as `IMPLEMENTED` in the plan.
   c. Update the progress dashboard.
5. **Quality gate check** (mandatory before shipping):
   Run the implement skill's Step 4 (Simplify via
   `code-simplifier:code-simplifier`) and Step 5 (Review via
   `feature-dev:code-reviewer` for spec compliance, then parallel
   `pr-review-toolkit:code-reviewer`,
   `pr-review-toolkit:silent-failure-hunter`, and
   `pr-review-toolkit:pr-test-analyzer` for code quality) on the
   combined diff of all phases. Do NOT ship code that has not been
   through both simplify and review.
6. **Ship** the batch using the **ship** skill (Steps 1–7):
   - The ship skill commits, pushes, creates the PR, and starts
     background monitoring via monitor-pr.
   - **Wait for the merge**. Poll every 2 minutes with
     `gh pr view <pr> --json state --jq '.state'`.
     - If state is `CLOSED`: alert the user and stop.
     - If state is `MERGED`: mark all batched phases as `MERGED`
       and proceed to Completion.

#### Split flow (large phases only)

For each remaining `TODO` phase, in order:

1. Print the progress dashboard.
2. Pull the latest main: `git pull origin <main-branch>`.
3. **Implement** the phase using the **implement** skill (Steps 1–7).
4. **Quality gate check**: Verify Steps 4 (Simplify via
   `code-simplifier:code-simplifier`) and 5 (Review via
   `feature-dev:code-reviewer`, `pr-review-toolkit:code-reviewer`,
   `pr-review-toolkit:silent-failure-hunter`,
   `pr-review-toolkit:pr-test-analyzer`) were executed. If either was
   skipped, run them now.
5. **Ship** the phase using the **ship** skill (Steps 1–7):
   - Wait for the merge as above.
   - **Strict sequential**: Do NOT start the next phase while the
     current PR is open. Each must be fully merged first.
6. `git pull origin <main-branch>`, then loop back for the next phase.

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

1. **Final sync**: `git pull origin <main-branch>` to ensure local
   main matches the remote after all merges.

2. **Print** the final progress dashboard (all phases showing `MERGED`).

3. **Update the plan**:
   - Mark `Ship` as `MERGED` in the plan's status table.
   - Rename the plan file to denote completion: `plan-<name>.md` →
     `plan-<name>-done.md` (use `git mv` if the file is tracked,
     otherwise plain `mv`). Skip if the file is already named
     `*-done.md` (monitor-pr may have renamed it first).
   - **Commit and push the rename** (use the resolved plan file path,
     not a hardcoded directory):
     `git add <plan-file-done-path> && git commit -m "mark plan complete" && git push origin <main-branch>`

4. **Clean up remote branches**: Delete any feature branches created
   during this run that still exist on origin:
   ```bash
   git fetch --prune origin
   ```
   Then for each branch created during the run that still exists
   remotely: `git push origin --delete <branch>`. Also delete
   corresponding local branches with `git branch -d <branch>` (use
   `-D` as fallback — safe because the PRs were merged).

5. Congratulate the user — the feature is complete.
6. Remind them of any deferred suggestions or follow-up items from
   reviews across all phases.
7. Print the workflow friction log (see below).

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

2. **`.claude/settings.local.json`** with permissions and sandbox
   config. A baseline template is provided at
   `../../shared-references/permissions-template.json`. Copy it and
   add project-specific entries:
   `cp <plugin-path>/shared-references/permissions-template.json .claude/settings.local.json`

   Then add your project-specific patterns (test runners, linters,
   language tools), e.g.:
   ```json
   "Bash(pytest:*)",
   "Bash(npm test:*)",
   "Bash(cargo test:*)"
   ```

   `CronCreate`, `CronDelete`, `CronList`, and `Agent` do not
   require explicit permission entries.

The `sandbox` block is the key to zero-prompt autonomous runs:
- `enabled: true` restricts file writes to the project directory
- `autoAllowBashIfSandboxed: true` auto-approves bash commands
  within that sandbox
- `excludedCommands: ["git", "gh"]` exempts git and gh from sandbox
  restrictions — without this, the sandbox denies writes to `.git/`
  internals and every git command falls back to
  `dangerouslyDisableSandbox`

Note: With `autoAllowBashIfSandboxed: true`, granular `Bash(git:*)`
permission entries are redundant for sandboxed commands — they only
matter if sandbox is disabled. They are included in the template as
a fallback.

If permissions are not configured, the skill still works but will
pause for user approval on each tool call — defeating the purpose
of autonomous mode. The Permission Pre-flight (Step 0) detects this
and tells the user what to configure.

## Notes

- Each phase goes through the full implement-ship cycle including all
  quality gates (simplify, deep review, CI). No shortcuts — the
  quality gate check in Step 2.3 enforces this.
- **Default: batch phases into one PR**. Implement all remaining
  phases in a single worktree and ship them as one PR. Only split
  phases into separate PRs when a phase is large enough to warrant
  independent review (substantial new feature, major refactor, or
  100+ lines of non-trivial changes). When in doubt, batch.
- **Strict sequential execution**: Each PR must be fully merged before
  the next one begins. No parallel PRs, no pipelining.
- Phases always branch from the latest main. After each PR merges,
  pull main before starting the next.
- If the user interrupts the loop, they can resume by invoking
  `/implement-ship-all` again — it reads the state file and plan
  status table to determine what's next.
- **Autonomous mode**: This skill runs with minimal user interaction.
  It only stops for genuine blockers (failed CI after 2+ retries,
  substantive review disagreements, ambiguous merge conflicts). All
  "Proceed?" prompts in sub-skills are skipped. The user can interrupt
  at any time and resume later.
- **User overrides**: If the user explicitly requests a different
  shipping strategy (e.g., "combine all phases into one PR" or
  "ship each phase separately"), acknowledge the quality gate
  tradeoff and proceed with their preference.

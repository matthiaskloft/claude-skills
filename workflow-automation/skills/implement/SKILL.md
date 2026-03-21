---
name: implement
description: >
  Implement a feature from a plan document, working phase by phase. Use when
  the user says "implement this plan", "start building", "implement phase",
  "work on phase", "/implement", "build from the plan", or references an
  existing plan document and wants to start coding. Also trigger when a plan
  was just approved and the user wants to proceed. Do NOT use for ad-hoc
  coding tasks without a plan — just code directly for those.
---

# Implement Phase — Build from a Plan

You are implementing a feature from an existing plan document, working
through it phase by phase.

## State Tracking

This skill uses `.workflow-state.json` for cross-session resume.
See `../../shared-references/workflow-state.md` for the full protocol.

**On startup**: Check for `.workflow-state.json` in the project root.
If found with `skill: "implement"` and the phase is still incomplete,
offer to resume from the recorded step. If stale, delete it and start
fresh.

**Autonomous mode**: If the state file contains
`mode: "implement-ship-all"` or `mode: "plan-implement-ship"`, skip all confirmation prompts:
- Resume automatically from the recorded step without asking
  "Resume or start over?"
- Step 2: Do not ask "Starting {phase}. Proceed?" — start immediately

**During execution**: Update the state file at Steps 2, 3, 5, and 7.

**On completion**: Clear the state file after Step 7 to ensure
deterministic resume behavior and a clean state for subsequent skills.

## Step-by-Step

### 1. Load the Plan

- Search for the plan document in this order:
  1. Check CLAUDE.md for a dev docs directory convention, look in its
     `plans/` subfolder
  2. Look for `plan-*.md` files in the project root
- Exclude files matching `plan-*-done.md` — these are completed plans.
  If only completed plans exist, inform the user that all plans are
  already done.
- If the user specifies a plan name, find the matching file.
- If multiple plans exist, show the user a list and ask which to use.
- Read the plan and identify which phases are `TODO` or `IN_PROGRESS`.
- Check that the Plan phase is marked `DONE` in the status table. If it's
  still `TODO` or `IN_PROGRESS`, the plan hasn't been approved — suggest
  completing the **plan** skill first.
- If no plan exists, ask the user: create a plan first (using the
  **plan** skill), or implement ad-hoc without one?

**Gitignore check**: Before writing `.workflow-state.json`, check if
`.gitignore` exists and contains `.workflow-state.json`. If the entry is
missing, append it (create `.gitignore` if needed). This prevents
accidental commits of local workflow state.

### 2. Select the Next Phase

- Identify incomplete work in the plan. Look for phases, steps, or sections
  marked as TODO/incomplete, or infer from context which parts haven't been
  done yet.
- If the plan has dependency information between phases, verify prerequisites
  are complete. If not, inform the user and ask whether to proceed anyway or
  work on the dependency first.
- If the user specified which phase to work on, start it directly. Otherwise,
  confirm with the user: "Starting {phase/section name}. This involves:
  {brief summary}. Proceed?"
- Mark the phase as in progress: update the status table if the plan has one,
  otherwise add a note at an appropriate place in the plan (e.g., inline next
  to the phase heading or in a Notes section).

### 3. Execute the Phase

Follow the plan's steps for this phase:
- Create and modify the files listed in the plan
- Write tests for new code and update existing tests for modified behavior
  — as part of the phase, not as a separate step
- Run tests after implementation to verify correctness
- Follow the project's conventions (check CLAUDE.md). If no CLAUDE.md
  exists, infer conventions from existing code and dev docs.

**Match existing patterns**: Before writing new code in a file, read the
entire file to identify architectural patterns already in use — wrapper
functions, factory conventions, registration patterns, naming schemes,
and API surface conventions. Replicate these patterns in new code. For
example, if existing functions follow a "public no-arg wrapper + private
parameterized implementation" pattern for a registry, new functions must
follow the same structure.

**Stay on scope**: Only implement what the plan specifies for this phase.
Before modifying a file, cross-check it against the plan's file lists for
this phase. If the file is not listed, stop and ask the user: add it to
the current phase, defer it to a future phase, or document it in the
project's dev docs todo file and continue.

After execution, determine the phase status (see Phase Execution
Statuses below). If the status is not `IMPLEMENTED`, handle according
to the protocol before proceeding.

### 4. Simplify

Run a simplification pass on the changed code to clean up
over-engineering, unnecessary abstractions, and code style issues before
review. Spawn an agent using the Agent tool
(`subagent_type="code-simplifier:code-simplifier"`, `model: "sonnet"`)
targeting the files modified in this phase.

If this agent type is unavailable, fall back to a general-purpose agent
with instructions to simplify the changed code for clarity and
maintainability.

### 5. Review Loop

Run a two-stage code review cycle until the code is clean.

**Stage 1 — Spec compliance** (mandatory, runs first):

Spawn an agent (`subagent_type="feature-dev:code-reviewer"`) with the
plan document and changed files. Focus prompt: "Verify that the
implementation matches the plan for this phase. Check: (1) all planned
steps were addressed, (2) no over-building beyond the plan's scope,
(3) pattern consistency — new code replicates the architectural patterns
established in the same file or module. For each finding, state severity
(blocker/warning/suggestion) and a concrete fix."

Fix any blockers or warnings, then re-run Stage 1. Cap at 2 iterations
— if spec compliance still has blockers after 2 rounds, stop and inform
the user.

**Stage 2 — Code quality** (only after Stage 1 passes):

Spawn three agents in parallel:
- `subagent_type="pr-review-toolkit:code-reviewer"` — project guidelines
  and CLAUDE.md conventions
- `subagent_type="pr-review-toolkit:silent-failure-hunter"` — error
  handling, swallowed exceptions, inappropriate fallback behavior
- `subagent_type="pr-review-toolkit:pr-test-analyzer"` — test coverage
  quality and critical gaps

Collect findings from all three. Fix blockers and warnings, then re-run
Stage 2. Cap at 3 iterations — if the 3rd iteration still has blockers,
stop and inform the user. Suggestions may be deferred — document them
in the plan's Notes section.

**Fallback**: If any agent type is unavailable, fall back to a
general-purpose agent with the same focus prompt.

See the **Agent Catalog** at the end of this file for the full list of
available agents and their roles.

### 6. Update Documentation

- Update code documentation (docstrings, comments, type annotations) for
  new or modified public APIs.
- Add inline comments for non-obvious logic, important design decisions,
  and "why" explanations — even in non-public code. The goal is that a
  reader unfamiliar with the codebase can follow the implementation.
- Update development docs if the phase changed architecture, conventions,
  or added concepts that future sessions need to know about.

### 7. Update the Plan

- Mark the phase with its execution status (see Phase Execution Statuses):
  update the status table if the plan has one, otherwise add a note at an
  appropriate place in the plan (e.g., inline next to the phase heading
  or in a Notes section).
- If the status is `IMPLEMENTED_WITH_CONCERNS`, record the concerns in
  the plan's Notes section so they are visible to the ship skill and
  the user.
- Document what happened: key implementation decisions, deviations from
  the plan, and blockers or issues discovered for future phases. Place
  this in the plan's Notes section if one exists, or add it near the
  completed phase.

### 8. Next Steps

After completing a phase, suggest using the **ship** skill to commit,
PR, and merge the phase. The ship skill will propose the next phase
after shipping is complete.

## Phase Execution Statuses

After executing a phase (Step 3), assign one of these statuses:

- **`IMPLEMENTED`** — phase complete, all tests pass, ready to ship.
- **`IMPLEMENTED_WITH_CONCERNS`** — complete and tests pass, but with
  flagged doubts (e.g., approach may not scale, test coverage is
  uncertain, edge case handling is unclear). Concerns are surfaced to
  the user before shipping. In autonomous mode
  (`mode: "implement-ship-all"` or `mode: "plan-implement-ship"`), log the concerns in the plan's Notes
  and proceed.
- **`NEEDS_INPUT`** — blocked on a user decision (e.g., ambiguous
  requirement, design choice not covered by the plan). In autonomous
  mode: log the question in the plan's Notes, mark the phase `BLOCKED`,
  and move to the next phase if it is independent; otherwise stop the
  loop.
- **`BLOCKED`** — cannot proceed due to a technical issue (missing
  dependency, unresolvable test failure, infrastructure problem).
  Triggers the stop-and-escalate protocol (see When to Stop and
  Escalate).

## When to Stop and Escalate

Stop fixing and escalate to the user when:

- **Blocker hit**: A missing dependency, unexpected test failure, or
  unclear instruction prevents progress. Do not guess — ask.
- **3+ fix attempts on the same issue**: Do not attempt fix #4. The
  pattern of repeated failures indicates the approach is wrong, not
  that the fix is almost right. Step back and question the approach.
- **You don't understand why something fails**: If you cannot explain
  the root cause, do not try random fixes. Ask for help.

**In autonomous mode** (`mode: "implement-ship-all"` or `mode: "plan-implement-ship"`): mark the phase
as `BLOCKED`, log what was tried and what failed in the plan's Notes
section, and stop the loop. Do not silently continue to the next phase
unless it is explicitly independent (no dependency on the blocked
phase).

## Branching

- Detect the main branch name (e.g., `main`, `master`) from the repo
- Pull the latest main: `git pull origin <main-branch>`
- Create a worktree for the phase:
  `git worktree add -b feat/<feature>-<phase> ../feat-<feature>-<phase> origin/<main-branch>`
- Work in the worktree directory
- The **ship** skill handles committing, PR, and cleanup
- If abandoning a phase, ask the user before deleting the worktree and branch

## Troubleshooting

- **Phase is taking too long**: Break it into sub-steps and commit
  intermediate progress. Update the plan to split the phase if needed.
- **Plan is outdated**: If the codebase has changed since planning, note
  the discrepancies and adjust. Update the plan document to reflect
  reality.
- **Tests fail unexpectedly**: Fix the issue if it's within the phase's
  scope. If it's a pre-existing problem, document it in Notes and
  continue. If fixes fail repeatedly, follow the stop-and-escalate
  protocol (see When to Stop and Escalate).
- **Blocked by a dependency**: See Phase Execution Statuses — mark the
  phase as `BLOCKED` or `NEEDS_INPUT` and follow the protocol there.
- **WSL git index lock**: On WSL2, the first `git add` or `git mv` in
  a worktree may fail with "Read-only file system" on the index.lock.
  Retry the same command — it typically succeeds on the second attempt.
  Do not treat this as a fatal error.

## Common Mistakes

- Implementing beyond the phase's scope ("while I'm here, I'll also...")
- Skipping tests to save time (tests are part of each phase, not optional)
- Not updating the plan document after completing a phase
- Starting the next phase without confirming the current one works
- Forgetting to check project conventions in CLAUDE.md
- Introducing a new pattern (e.g., direct implementation) when the file's
  existing functions use a wrapper/factory convention — replicate the
  existing structure instead

## Agent Catalog

Agents available to the workflow automation skills. The plan skill uses
`feature-dev:code-architect` for plan review — see plan/SKILL.md Step 3.

**Review agents:**
- `feature-dev:code-reviewer` — bugs, logic errors, security
  vulnerabilities, code quality (confidence-filtered)
- `pr-review-toolkit:code-reviewer` — project guidelines, CLAUDE.md
  conventions, style guides
- `pr-review-toolkit:silent-failure-hunter` — error handling, swallowed
  exceptions, inappropriate fallback behavior
- `pr-review-toolkit:pr-test-analyzer` — test coverage quality and gaps
- `pr-review-toolkit:comment-analyzer` — comment accuracy and
  completeness
- `pr-review-toolkit:type-design-analyzer` — type design, encapsulation,
  invariant expression

**Implementation agents:**
- `code-simplifier:code-simplifier` — simplify code for clarity and
  maintainability
- `feature-dev:code-architect` — design architectures from existing
  codebase patterns
- `feature-dev:code-explorer` — trace execution paths, map architecture,
  understand dependencies

**Exploration agents:**
- `Explore` — fast codebase search (general purpose only; do NOT use
  for code review or simplification — use the dedicated agents above)
- `Plan` — implementation strategy design

## Model Selection Guidance

Use `model: "sonnet"` for the simplification agent (Step 4) — it is
mechanical and benefits from speed over depth. Use the default model
for all review agents and tasks requiring deep reasoning (spec
compliance, architectural analysis, complex multi-file changes).

The user can override model choices via CLAUDE.md preferences.

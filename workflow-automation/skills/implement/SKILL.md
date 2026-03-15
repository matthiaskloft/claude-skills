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
`mode: "implement-ship-all"`, skip all confirmation prompts:
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

### 4. Simplify

Run a simplification pass on the changed code to clean up over-engineering,
unnecessary abstractions, and code style issues before review. Use a
dedicated simplify skill if one is available in the user's system. If not,
spawn an independent agent to review the changed code for unnecessary
complexity, dead code, and style inconsistencies, and apply the fixes.

### 5. Deep Review Loop

Run a comprehensive code review cycle until the code is clean:

1. Check if a dedicated code review skill or agent is available. Prefer
   one that reviews against the broader codebase (not just the diff in
   isolation), checks for redundancies with existing code, and returns
   structured findings with severity levels. If none is available, spawn
   an independent review agent (`subagent_type=Explore`) with this prompt:
   "Review the following changed files against the broader codebase.
   Check for: (1) plan compliance — were all planned steps addressed,
   (2) redundancies — does new code duplicate existing utilities,
   (3) correctness — edge cases, return value contracts, error handling,
   (4) security — injection, path traversal, credential exposure,
   (5) coherence — do changes break callers or violate conventions,
   (6) pattern consistency — does new code replicate the architectural
   patterns (wrappers, factories, registration, naming) established in
   the same file or module, rather than introducing a different style.
   For each finding, state severity (blocker/warning/suggestion) and a
   concrete fix. End with: Review complete: X findings."
   Pass the plan document, changed files, and relevant surrounding code.

2. If the review reports findings: fix them and run the review again.

3. Repeat until no fixes were needed — i.e., zero blockers or warnings
   remain. Suggestions may be deferred — document them in the plan's Notes
   section and continue.

   Cap at 4 total review iterations. If the 4th review still returns
   blockers or warnings that require fixes, stop and inform the user
   rather than starting another fix/review cycle.

### 6. Update Documentation

- Update code documentation (docstrings, comments, type annotations) for
  new or modified public APIs.
- Add inline comments for non-obvious logic, important design decisions,
  and "why" explanations — even in non-public code. The goal is that a
  reader unfamiliar with the codebase can follow the implementation.
- Update development docs if the phase changed architecture, conventions,
  or added concepts that future sessions need to know about.

### 7. Update the Plan

- Mark the phase as `IMPLEMENTED`: update the status table if the plan has
  one, otherwise add a note at an appropriate place in the plan (e.g.,
  inline next to the phase heading or in a Notes section).
- Document what happened: key implementation decisions, deviations from
  the plan, and blockers or issues discovered for future phases. Place
  this in the plan's Notes section if one exists, or add it near the
  completed phase.

### 8. Next Steps

After completing a phase, suggest using the **ship** skill to commit,
PR, and merge the phase. The ship skill will propose the next phase
after shipping is complete.

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
  scope. If it's a pre-existing problem, document it in Notes and continue.
- **Blocked by a dependency**: Note the blocker in the plan, mark the
  phase as `BLOCKED`, and ask the user how to proceed.
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

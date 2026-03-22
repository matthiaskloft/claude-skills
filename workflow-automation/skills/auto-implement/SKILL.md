---
name: auto-implement
description: >
  Plan, implement, and ship a feature end-to-end. Use when the user says
  "plan and ship", "auto-implement", "/auto-implement", "design and build",
  "plan then implement and ship", "plan and build this", "implement
  everything", "ship all phases", "autopilot", "autopilot this",
  "/autopilot", "do this autonomously", "build autonomously",
  "build and merge everything", or wants to go from idea (or existing
  plan) to fully merged feature without stopping. Also triggered from
  brainstorm hand-off when user selects "Plan and ship". Works with or
  without an existing plan — skips planning if a plan is already approved.
  Do NOT use for tasks small enough to implement directly without planning.
---

# Auto-Implement — Design to Merged PR

You are planning a feature, implementing it, and shipping it — all in
one flow. This skill is the single entry point for the complete pipeline.

It handles all scenarios:
- **No plan exists** → plan → implement all phases → ship
- **Spec exists but no implementation plan** → ask user (see Step 1)
- **Plan exists but unapproved** → resume/complete planning → implement → ship
- **Plan exists and approved** → skip planning → implement remaining phases → ship

## State Tracking

This skill delegates to **feature-plan**, **implement**, and **ship**,
which handle their own state tracking via `.workflow-state.json`. The
`mode` field is set to `"auto-implement"`.

**On startup**: Check for `.workflow-state.json`. If found with
`mode: "auto-implement"`:
- If `pr_number` is set, check the PR status. If merged, clear it
  and continue. If open, verify monitor-pr is active (re-create the
  cron if the session died).
- Read the plan's status table. If `Plan` is `DONE`, find the next
  `TODO` or `IN_PROGRESS` phase and resume the loop.
- If `Plan` is `TODO` or `IN_PROGRESS`, resume planning.
- If no plan file exists, start fresh.

Print "Resuming auto-implement from {stage}" and continue — do
not re-confirm.

## Step-by-Step

### 0. Permission and Sandbox Pre-flight

Follow the pre-flight protocol in
`../../shared-references/autonomous-permissions.md`. Only proceed to
Step 1 when all test commands pass without prompts.

### 1. Plan

Check for an existing plan:
- Search for `plan-*.md` (exclude `*-done.md`) in the dev docs `plans/`
  subfolder and project root.
- If a plan exists with `Plan` marked `DONE`, skip to Step 2.
- If a plan exists with `Plan` as `TODO` or `IN_PROGRESS`, resume
  planning from where it left off.
- If no plan exists, run the **feature-plan** skill in full (Steps 1–5).

**Spec-only plan** (Spec is `DONE` but Plan is `TODO`): The plan file
has a completed Spec section (from `/brainstorm`) but no implementation
phases yet. Ask the user:

> "This plan has a spec but no implementation phases yet. How would you
> like to proceed?"
>
> 1. **Plan and auto-implement** — Create phased implementation plan,
>    then immediately implement and ship all phases
> 2. **Plan only** — Create the implementation plan for review; I'll
>    implement later with `/auto-implement`

If the user selects option 1: run the **feature-plan** skill to add
implementation phases, then proceed directly to Step 2 (no stop).

If the user selects option 2: run the **feature-plan** skill to add
implementation phases, then stop after presenting the plan for approval.
The user can invoke `/auto-implement` again later to pick up from
Step 2.

**Key difference from standalone `/feature-plan`**: When proceeding to
auto-implement (option 1, or when this skill created the plan from
scratch), after the user approves the plan do NOT stop and suggest next
steps. Instead, proceed directly to Step 2.

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

Identify all phases marked `TODO`. Print the progress dashboard
(see `../../shared-references/autonomous-reporting.md`) and a summary:
"Starting autonomous run: {N} phases remaining. Will only stop for
blockers." Then begin immediately — do not ask for confirmation.

**Default: batch all phases into one PR.** Most plan phases are
tightly coupled and per-phase PRs create unnecessary overhead.
Implement all remaining `TODO` phases sequentially in a single
worktree, then ship once.

**Exception: split mid-batch** when a phase turns out to be large
after implementation (100+ non-trivial lines in its diff, excluding
tests, config, and imports). The decision is made after each phase's
implementation, not before. If a phase exceeds the threshold:
1. Ship all previously implemented phases as one PR (the batch so far).
2. Wait for that PR to merge.
3. Pull latest main, then continue with the large phase in its own
   worktree and PR.
4. Resume batching for subsequent phases.

#### Batched flow (default)

1. Pull the latest main: `git pull origin <main-branch>`.
2. Create a single worktree for the batch.
3. Print the progress dashboard.
4. For each remaining `TODO` phase, in order:
   a. **Implement** the phase using the **implement** skill
      (Steps 1–7; Step 8 is skipped — auto-implement handles
      sequencing). The implement skill detects `mode: "auto-implement"`
      and skips all confirmation prompts. If implementation fails
      or is blocked, stop the loop and inform the user — later phases
      may depend on this one.
   b. **Gate check** after implementation:
      - `IMPLEMENTED` → continue to next phase.
      - `IMPLEMENTED_WITH_CONCERNS` → log concerns in the plan's Notes
        and continue.
      - `BLOCKED`, `NEEDS_INPUT`, or incomplete → stop the loop and
        inform the user.
   c. Update the progress dashboard.
5. **Combined quality gate** (mandatory before shipping):
   Run simplify (via `code-simplifier:code-simplifier`) and review
   (via `feature-dev:code-reviewer` for spec compliance against the
   full plan, then parallel `pr-review-toolkit:code-reviewer`,
   `pr-review-toolkit:silent-failure-hunter`, and
   `pr-review-toolkit:pr-test-analyzer` for code quality) on the
   combined diff of all phases. Spec compliance checks all phases
   against the full plan, not per-phase. Do NOT ship code that has
   not been through both simplify and review.
   If the combined quality gate still has unresolved blockers after
   hitting iteration caps, mark all batched phases as
   `IMPLEMENTED_WITH_CONCERNS` in the plan and surface the findings.
   **This is a hard stop even in autonomous mode** — combined-gate
   blockers indicate cross-phase issues that per-phase reviews missed.
   Do not proceed to ship. Present the unresolved findings and ask the
   user for guidance.
6. **Ship** the batch using the **ship** skill (Steps 1–7):
   - The ship skill commits, pushes, creates the PR, and starts
     background monitoring via monitor-pr.
   - **Wait for the merge**. Poll every 2 minutes with
     `gh pr view <pr> --json state --jq '.state'`.
     - If state is `CLOSED`: alert the user and stop.
     - If state is `MERGED`: mark all batched phases as `MERGED`
       and proceed to Completion.

#### Split flow (triggered mid-batch by large phase)

When a phase exceeds the size threshold after implementation:

1. **Ship the batch so far**: Run the quality gate and ship skill on
   all previously implemented phases. Wait for the PR to merge.
2. `git pull origin <main-branch>`.
3. Print the progress dashboard.
4. Create a new worktree for the large phase.
5. **Implement** the phase using the **implement** skill (Steps 1–7).
6. **Quality gate check**: Run Steps 4 (Simplify) and 5 (Review) on
   this phase's diff.
7. **Ship** the phase using the **ship** skill (Steps 1–7):
   - Wait for the merge.
   - **Strict sequential**: Do NOT start the next phase while the
     current PR is open. Each must be fully merged first.
8. `git pull origin <main-branch>`, then resume batching for remaining
   phases (create a new worktree, continue the loop).

**After the last phase is shipped and merged**, proceed to Completion.

### 4. Completion

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

5. **Write deferred items**: Collect all deferred suggestions and
   follow-up items from reviews across all phases. Add each to the
   project's dev docs TODO file (see
   `../../shared-references/todo-convention.md`) with the originating
   phase as source. If no items were deferred, skip this step.

6. Congratulate the user — the feature is complete.
7. Print the workflow friction log (see
   `../../shared-references/autonomous-reporting.md`).

## Notes

- Each phase goes through the full implement → ship cycle including all
  quality gates (simplify, deep review, CI). No shortcuts.
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
  `/auto-implement` again — it reads the state file and plan
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
- For features where the design needs more exploration first, suggest
  `/brainstorm` before `/auto-implement`.
- The feature-plan skill's review loop and the implement skill's quality
  gates all run — no shortcuts. The full pipeline is:
  brainstorm (optional) → feature-plan (with review) → implement (with
  simplify + review) → ship (with CI + merge).

---
name: ship
description: >
  Ship a completed phase: commit, create a PR, monitor CI, and merge. Use when
  the user says "ship this", "create a PR", "open a pull request", "commit and
  push", "ship the phase", "/ship", "merge this", or has just finished
  implementing a phase and wants to get it merged. Also trigger when the
  implement skill suggests shipping after completing a phase. Do NOT use for
  routine commits without PR intent — use a commit skill or git directly.
---

# Ship Phase — Commit, PR, and Merge

You are shipping a completed implementation phase: committing the changes,
opening a pull request, monitoring CI, and merging.

## State Tracking

This skill uses `.workflow-state.json` for cross-session resume.
See `../../shared-references/workflow-state.md` for the full protocol.

**On startup**: Check for `.workflow-state.json` in the project root.
If found with `skill: "ship"` and the phase is not yet merged, resume
from the recorded step. Key resume scenarios:
- `step: 2` — changes were staged/committed but not pushed. Push and
  continue from Step 3.
- `step: 3` with `pr_number` set — PR was created. Skip to Step 4.
- `step: 4` with `monitor_cron_id` set — monitoring was active. Check
  if the cron job still exists (CronList); if not, re-invoke monitor-pr.

**Autonomous mode**: If the state file contains
`mode: "implement-ship-all"` or `mode: "plan-implement-ship"`, skip all confirmation prompts:
- Resume automatically from the recorded step without asking
  "Resume or start over?"
- Step 1: If the phase is `IMPLEMENTED`, proceed directly without
  asking whether to finalize

**During execution**: Update the state file at Steps 2, 3, and 4.

**On completion**: The monitor-pr skill clears the state file after
successful merge.

## Step-by-Step

### 1. Verify Readiness

Before shipping, confirm the phase is ready:

**Read state file**: At the start of this step, read `.workflow-state.json`
if it exists and extract the `mode` field.

**If `mode` is `"implement-ship"` or `"implement-ship-all"`** (ship is
part of a combined flow): skip the fresh test/build verification —
implement just ran tests moments ago in the same session. Still check
plan status below.

**Otherwise (standalone ship)**: Run the project's test command (infer
from CLAUDE.md, CI config, or common conventions like `npm test`,
`pytest`, `cargo test`, `devtools::test()`, etc.) and read the full
output — exit code, pass/fail counts. Do not rely on "tests passed
during implementation" — that was a different context. Run the build
command if applicable and verify exit 0. If you cannot produce fresh
test output showing 0 failures, do not proceed to Step 2. Fix the
issues first.

**Plan status check** (always, regardless of mode):
- If a plan document exists, verify the current phase is marked
  `IMPLEMENTED` or `IMPLEMENTED_WITH_CONCERNS` (not `IN_PROGRESS` or
  `TODO`). If it's still in progress, ask the user whether to finalize
  it first or ship as-is.
- If the phase is `IMPLEMENTED_WITH_CONCERNS`, surface the concerns to
  the user and ask whether to proceed. In autonomous mode
  (`mode: "implement-ship-all"` or `mode: "plan-implement-ship"`), log the concerns in the plan's Notes
  and proceed — the implement skill already surfaced them.
- Mark the `Ship` phase as `IN_PROGRESS` in the plan's status table (or
  add a note if no status table exists).

Do not ship broken code.

### 2. Stage and Commit

- Run `git status` and `git diff` to review all changes
- Stage the relevant files. Prefer staging specific files over `git add .`
  to avoid accidentally committing secrets, build artifacts, or unrelated
  changes.
- Do NOT stage files that likely contain secrets (`.env`, credentials,
  API keys, tokens). Warn the user if such files are in the working tree.
- Do NOT stage `.workflow-state.json` — it is local workflow state, not
  project content.
- Write a clear commit message:
  - First line: concise summary of what the phase accomplished (under 72 chars)
  - Body: brief explanation of key changes if the diff is non-trivial
  - Follow the project's commit message conventions if documented in
    CLAUDE.md or inferable from `git log`
- If the changes are large, consider splitting into logical commits (one
  per concern) rather than a single monolithic commit.
- Update the phase status to `COMMITTED` in the plan's status table.

### 3. Push and Create PR

- Push the branch to the remote:
  `git push -u origin <branch-name>`
- Check for PR templates in `.github/PULL_REQUEST_TEMPLATE.md` or
  `.github/pull_request_template.md`. If found, read and fill out the
  template. Otherwise use the default format below.
- Create a pull request using `gh pr create`:
  - **Title**: Short, descriptive (under 70 chars). Follow project conventions.
  - **Body**: Include:
    - Summary of what was implemented (reference the plan if one exists)
    - Key design decisions or trade-offs worth noting for reviewers
    - Test plan: how to verify the changes work
  - Target the main branch (detect from repo, e.g., `main`, `master`)
- Default PR format:

  ```
  ## Summary
  <bullet points>

  ## Test Plan
  <how to verify>
  ```

### 4. Monitor and Merge

Delegate CI monitoring and auto-merge to the **monitor-pr** skill:

- Invoke `/monitor-pr` with the PR number from Step 3.
- monitor-pr sets up a background cron job (every ~5 min) that checks
  CI, fixes failures, and auto-merges when ready.
- It also handles post-merge cleanup (worktree removal, branch
  deletion, pulling latest main).

After monitor-pr creates the cron job, wait for the merge to complete.
Poll every 2 minutes with
`gh pr view <pr-number> --json state --jq '.state'` until the state is
`MERGED`. Then continue to Step 5. (The user can interrupt this polling
at any time — monitor-pr continues in the background.)

If monitor-pr reports a blocker needing human input, help the user
resolve it, then re-invoke `/monitor-pr` to resume.

### 5. Post-Merge Verification

The **monitor-pr** skill handles cleanup. Verify it completed:

- Run `git worktree list` to confirm the worktree is removed
- Run `git branch` to confirm the feature branch is deleted
- If cleanup was incomplete (e.g., monitor-pr was interrupted),
  perform it manually:
  1. Return to the main repository directory
  2. `git worktree remove ../feat-<feature>-<phase>` (if worktree exists)
  3. `git branch -d feat/<feature>-<phase>` (if branch exists)
  4. `git pull origin <main-branch>`

### 6. Update the Plan

After the PR is merged, **always** update the plan file — do not assume
monitor-pr already did this:
1. Read the plan file and check the status table for the current phase
2. If the phase is not already `MERGED`:
   - Mark the phase as `MERGED` in the status table
   - Add the PR URL/number to the phase's Notes column
3. Record any deviations, follow-up items, or issues discovered during
   shipping
4. Commit and push the plan update (can be a separate commit on main)
5. If no plan document exists, ask the user if they want to track the
   shipped work anywhere.

### 7. Propose Next Steps

- Check the plan for remaining phases marked `TODO`
- If there are more phases:
  - Summarize the next phase and what it involves
  - Suggest starting it with the **implement** skill
- If all phases are done:
  - Mark `Ship` as `MERGED` in the status table
  - Rename the plan file to denote completion: `plan-<name>.md` →
    `plan-<name>-done.md` (use `git mv` if the file is tracked,
    otherwise plain `mv`). Skip if already named `*-done.md`.
  - Congratulate the user — the feature is complete
- If there are deferred suggestions or follow-up items from reviews,
  remind the user about them

## Branching

This skill works with the branch created by the **implement** skill:
- Branch naming: `feat/<feature>-<phase>`
- Worktree location: `../feat-<feature>-<phase>`
- If no worktree exists (user implemented on a regular branch), ship
  from whatever branch is currently checked out
- Detect the main branch name from the repo (e.g., `main`, `master`)

## Troubleshooting

- **CI fails on unrelated tests**: Note it in the PR, inform the user,
  and ask whether to merge anyway or investigate.
- **Merge conflicts**: Rebase the branch on the latest main branch,
  resolve conflicts, and push. Ask the user for help with ambiguous
  conflict resolution.
- **PR requires approvals**: Inform the user that human review is needed.
  Do not bypass review requirements.
- **Worktree already removed**: Skip cleanup. Verify the branch was
  deleted; if not, clean it up manually.
- **No plan document**: Ship normally without plan updates. Ask the user
  if they want to track the shipped work anywhere.

## Common Mistakes

- Force-pushing or using `--no-verify` to bypass failing checks
- Committing secrets, `.env` files, or build artifacts
- Merging without CI passing
- Not cleaning up worktrees and branches after merge
- Forgetting to update the plan document after shipping
- Creating a monolithic commit instead of logical, reviewable chunks
- Amending commits to fix CI instead of creating separate fix commits

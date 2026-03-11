---
name: monitor-pr
description: >
  Monitor a PR's CI status in the background and auto-merge when ready. Use when
  the user says "monitor this PR", "watch CI", "monitor-pr", "/monitor-pr",
  "watch the checks", "let me know when CI passes", or when the ship skill
  reaches its monitoring step (Step 4). Takes an optional PR number — if omitted,
  detects the PR from the current branch. Do NOT use before a PR exists — use
  the ship skill to create the PR first.
---

# Monitor PR — Background CI Monitoring and Auto-Merge

You are setting up background monitoring for a pull request. Once started,
a cron job checks CI status every 4 minutes and takes autonomous action:
fixing failures, responding to simple review feedback, and merging when
all checks pass.

## State Tracking

This skill uses `.workflow-state.json` for cross-session resume.
See `../../shared-references/workflow-state.md` for the full protocol.

**On startup**: Check for `.workflow-state.json` with
`skill: "monitor-pr"` and a `monitor_cron_id`. If found, the previous
session was monitoring this PR. Check if the PR is still open
(`gh pr view`). If open, re-gather context from Step 2 (branch,
worktree, merge strategy), then skip to Step 4 to create a new cron
job (the old one died with the previous session). If merged/closed,
clear the state file and stop.

**During execution**: Update the state file at Step 4 with the
`monitor_cron_id`.

**On completion**: Delete the state file after successful merge and
cleanup.

## Step-by-Step

### 1. Identify the PR

- If the user provided a PR number, use it.
- Otherwise, detect it from the current branch:
  `gh pr view --json number --jq '.number'`
- If no PR is found, tell the user to create one first (suggest the
  **ship** skill) and stop.
- Validate the PR is open:
  `gh pr view <pr-number> --json state --jq '.state'`
  If it is already merged or closed, inform the user and stop.

### 2. Gather Context

Collect the information needed for the cron prompt:
- **PR number**: from Step 1
- **Branch name**:
  `gh pr view <pr-number> --json headRefName --jq '.headRefName'`
- **Worktree path**: Check if a worktree exists for this branch via
  `git worktree list` and look for the branch name. Record the path
  if found, otherwise record `none`.
- **Merge strategy**: Check CLAUDE.md or repo settings for convention.
  Default to `--squash`.
- **Main branch**: Detect from repo (e.g., `main`, `master`).
- **Plan file**: Resolve the plan document path (check CLAUDE.md for
  dev docs convention, then look for `plan-*.md` excluding
  `plan-*-done.md`). Record the path if found, otherwise record `none`.

### 3. Pre-flight Checks

Before creating the cron job:

- **Validate branch name**: Verify the branch name contains only safe
  characters (`a-zA-Z0-9/_.-`). If it contains shell metacharacters
  (`;`, `&`, `|`, `$`, backticks, spaces, etc.), refuse to monitor
  and warn the user — a malicious branch name could inject commands
  into the cron prompt. Similarly validate the worktree path.
- Check if any existing cron jobs already monitor this PR: use
  CronList and look for the PR number in existing prompts. If found,
  inform the user and ask whether to replace the existing monitor or
  keep it.

### 4. Create the Monitoring Cron Job

Use **CronCreate** with:
- **cron**: `"*/4 * * * *"` (every 4 minutes)
- **recurring**: `true`
- **prompt**: The monitoring prompt from the Cron Prompt section below,
  with all placeholders replaced with actual values.

Inform the user:

> Monitoring PR #{number} (`{branch}`). Checking CI every ~4 minutes.
> Will auto-merge when ready. Cron job ID: `{id}`.
>
> I'll only interrupt you for: ambiguous merge conflicts, review
> comments needing your judgment, or repeated CI failures (>2 attempts).
>
> Note: monitoring auto-expires after 3 days.

### 5. Post-Merge Cleanup

When the cron prompt detects a successful merge, it performs cleanup:

- **Worktree cleanup** (if a worktree path was recorded):
  1. Ensure the working directory is NOT in the worktree
  2. `git worktree remove <worktree-path>`
  3. If the local branch still exists: `git branch -d <branch-name>`

- **Pull latest main**: `git pull origin <main-branch>`

- **Update plan** (if a plan document exists):
  - Mark the phase as `MERGED` in the status table
  - Add the PR URL to the phase's Notes column
  - Check for remaining `TODO` phases and inform the user
  - If no `TODO` phases remain, rename the plan file to denote
    completion: `plan-<name>.md` → `plan-<name>-done.md`
    (use `git mv` if tracked, otherwise plain `mv`; commit the rename)

### 6. Cancellation

Monitoring stops automatically when:
- The PR is merged (success)
- The PR is closed externally
- Fix attempts exceed the threshold (>2 `fix(ci):` commits)
- The cron job auto-expires (3-day limit)

The user can stop monitoring manually by saying "stop monitoring" or
"cancel monitoring" — use CronDelete with the job ID.

## Cron Prompt

The following is the prompt text to use with CronCreate. Replace
`{pr_number}`, `{branch}`, `{worktree_path}`, `{merge_strategy}`,
`{main_branch}`, `{cron_job_id}`, `{mode}`, and `{plan_file}` with
actual values at creation time. `{mode}` is the workflow mode from the
state file (`single`, `implement-ship`, or `implement-ship-all`).
`{plan_file}` is the resolved path to the plan document (e.g.,
`dev/plans/plan-my-feature.md`), or `none` if no plan exists.

```
Check the status of PR #{pr_number} (branch: {branch}) and take action:

1. Check PR state:
   gh pr view {pr_number} --json state,mergeable,reviewDecision --jq '.'
   - If state is MERGED or CLOSED: cancel this cron job (CronDelete job {cron_job_id}), say "PR #{pr_number} was closed/merged externally. Monitoring stopped." and stop.

2. Check CI status:
   First check if any checks exist: gh pr view {pr_number} --json statusCheckRollup --jq '.statusCheckRollup | length'
   - If the count is 0 (no CI checks configured): skip to step 4 — treat as "all clear."
   - If checks exist, run: gh pr checks {pr_number}
     - If any checks are pending: say "PR #{pr_number}: checks still running." and stop.
     - If all checks passed: skip to step 4.
     - If any checks failed: continue to step 3.

3. CI failure handling:
   a. Count prior fix attempts: git log --oneline origin/{main_branch}..origin/{branch} --grep="fix(ci):" | wc -l
   b. If count > 2: cancel this cron job (CronDelete job {cron_job_id}). Tell the user: "PR #{pr_number} has failed CI {count} times. Stopping monitor — please investigate manually."
   c. If count <= 2: get the failed run ID with gh run list --branch {branch} --status failure --limit 1 --json databaseId --jq '.[0].databaseId', then read logs with gh run view <run-id> --log-failed. Diagnose and fix the issue if straightforward (test failures, lint errors, type errors, missing imports). Commit with message "fix(ci): <description>" and push to {branch}. If the failure is ambiguous or infrastructure-related, tell the user and wait for next cycle. Stop after pushing — next cycle will check results.

4. Merge readiness (all CI checks passed):
   a. If reviewDecision is CHANGES_REQUESTED: read review comments with gh api repos/:owner/:repo/pulls/{pr_number}/reviews. Address simple feedback (typos, naming, small fixes), commit and push. For substantive design disagreements, tell the user and wait.
   b. If reviewDecision is REVIEW_REQUIRED: tell the user approvals are needed (do this once — check if you already said this recently before repeating).
   c. If mergeable is CONFLICTING: attempt rebase onto {main_branch}. If conflicts are trivial (import ordering, whitespace), resolve, commit, push. If ambiguous, tell the user and wait.
   d. If mergeable is UNKNOWN: wait for next cycle.

   e. If reviewDecision is any other unexpected value: tell the user
      about the review state and wait for next cycle.

5. All clear (reviewDecision is APPROVED or empty, mergeable is MERGEABLE) — merge:
   gh pr merge {pr_number} {merge_strategy} --delete-branch
   - On success: cancel this cron job (CronDelete job {cron_job_id}). Say "PR #{pr_number} merged successfully."
     Then clean up:
     a. Check whether this branch is checked out in any other worktree by running: git worktree list --porcelain | grep -F "branch refs/heads/{branch}". If it is, do NOT delete the local branch — a successor phase may need it for rebase. Only delete the worktree (if path is not "none") with git worktree remove {worktree_path}.
     b. If the branch is not checked out in any other worktree: remove the worktree (if not "none") with git worktree remove {worktree_path}, and delete the local branch with git branch -d {branch}.
     c. Run git pull origin {main_branch}.
     If {plan_file} is not "none": update the current phase to MERGED with the PR URL in {plan_file}, then check remaining TODO phases: TODO_COUNT=$(grep -c "| TODO |" "{plan_file}" || echo "0"). If TODO_COUNT is 0, rename the plan: git mv "{plan_file}" "{plan_file%.md}-done.md" 2>/dev/null || mv "{plan_file}" "{plan_file%.md}-done.md" && git commit -m "mark plan complete". Inform the user of remaining phases or completion. If {plan_file} is "none", skip plan updates.
     d. Update .workflow-state.json based on {mode}:
        - If mode is "implement-ship-all":
          If {plan_file} is not "none" and TODO_COUNT is 0 (all phases done): rm .workflow-state.json (pipeline complete).
          Otherwise (phases remain, or no plan file): clear in_flight_pr (the predecessor merged, but successor tracking continues):
          jq '.in_flight_pr = null' .workflow-state.json > .workflow-state.json.tmp && mv .workflow-state.json.tmp .workflow-state.json
        - If mode is "single" or "implement-ship": delete the state file:
          rm .workflow-state.json
   - On failure: report the error to the user. Do NOT cancel monitoring — the issue may resolve on the next cycle.
```

## Edge Cases

- **Session ends before merge**: Cron job is lost. PR remains open.
  User re-invokes `/monitor-pr` in a new session to resume.
- **Multiple monitors on same PR**: Pre-flight check (Step 3) catches
  this and asks the user.
- **PR updated externally**: Monitor picks up new CI status naturally
  on next cycle. No special handling needed.
- **No CI checks configured**: `gh pr checks` returns exit code 1 when
  there are no checks, which looks like a failure. The cron prompt
  handles this by checking the check count first and treating zero
  checks as "all clear."
- **Repo requires specific merge method**: If `gh pr merge` fails due
  to strategy mismatch, retry with the allowed method.
- **Rate limiting**: If `gh` commands fail with rate limit errors,
  wait for next cycle.
- **Protected branches**: If merge fails due to branch protection
  rules the monitor can't satisfy, inform the user and continue
  monitoring.
- **Pipeline mode — successor branch depends on this branch**: The
  cron checks for dependent branches before deleting the local branch
  after merge. If a successor phase's branch was based on this one,
  the local branch is preserved until the successor rebases onto main.

## Common Mistakes

- Starting monitoring before the PR exists
- Not cancelling the cron job after merge (leads to error noise)
- Force-pushing to fix CI instead of creating new commits
- Amending commits instead of creating separate fix commits
- Repeatedly notifying the user about pending approvals every cycle
- Attempting to fix flaky/infrastructure CI failures with code changes
- Not checking for existing monitors before creating a duplicate

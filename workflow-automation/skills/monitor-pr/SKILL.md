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
a cron job checks CI status every 5 minutes and takes autonomous action:
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
- **SSH connectivity check**: Test that git can reach the remote:
  `git ls-remote --exit-code origin HEAD`
  If this fails (DNS resolution, SSH timeout), automatically switch
  the remote URL to HTTPS:
  `git remote set-url origin "$(gh repo view --json url --jq '.url').git"`
  Record the original URL so it can be restored after monitoring
  completes. Add `REMOTE_URL_SWITCHED=true` to the cron prompt
  context so post-merge cleanup can restore it.
- Check if any existing cron jobs already monitor this PR: use
  CronList and look for the PR number in existing prompts. If found,
  inform the user and ask whether to replace the existing monitor or
  keep it.

### 4. Create the Monitoring Cron Job

Use **CronCreate** with:
- **cron**: `"*/5 * * * *"` (every 5 minutes)
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

### 5. Pre-Merge Review and Post-Merge Cleanup

When the cron prompt reaches the "all clear" path, it performs a bot
review triage before merging, then cleans up after a successful merge:

- **Bot review triage** (before merge): Check for actionable inline
  review comments from automated reviewers (CodeRabbit, Copilot). If
  found, fix and push; next cycle will re-check. Caps at 6 fix attempts.

- **Worktree cleanup** (if a worktree path was recorded):
  1. Ensure the working directory is the main repo root (use
     `git worktree list` to find it, not `git rev-parse --show-toplevel`)
  2. `git worktree remove --force <worktree-path>`
  3. If the local branch still exists: `git branch -d <branch-name>`
     (use `-D` as fallback — safe because the PR was just merged)

- **Pull latest main**: `git pull origin <main-branch>`. If it fails
  due to uncommitted local changes, report the error — do not stash
  automatically.

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
- CI fix attempts exceed the threshold (>2 `fix(ci):` commits)
- Review fix attempts exceed the threshold (>6 `fix(review):` commits)
- The cron job auto-expires (3-day limit)

The user can stop monitoring manually by saying "stop monitoring" or
"cancel monitoring" — use CronDelete with the job ID.

## Cron Prompt

The following is the prompt text to use with CronCreate. Replace
`{pr_number}`, `{branch}`, `{worktree_path}`, `{merge_strategy}`,
`{main_branch}`, `{cron_job_id}`, `{plan_file}`,
`{original_remote_url}`, and `{remote_url_switched}` with actual
values at creation time.
`{plan_file}` is the resolved path to the plan document (e.g.,
`dev/plans/plan-my-feature.md`), or `none` if no plan exists.
`{original_remote_url}` is the remote URL recorded before any
SSH→HTTPS switch, or `none` if no switch occurred.
`{remote_url_switched}` is `true` if the remote was switched to
HTTPS during pre-flight, otherwise `false`.

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
   a. Pre-existing failure check: before attempting a fix, check if main also fails:
      gh run list --branch {main_branch} --limit 1 --json conclusion --jq '.[0].conclusion'
      If main's latest run also failed, compare the failing job names on both branches. If the same jobs fail on both, this is a pre-existing failure — log "PR #{pr_number}: CI failures match main branch (pre-existing). Proceeding to merge readiness." and skip to step 4.
   b. Count prior fix attempts: git log --oneline origin/{main_branch}..origin/{branch} --grep="fix(ci):" | wc -l
   c. If count > 2: cancel this cron job (CronDelete job {cron_job_id}). Tell the user: "PR #{pr_number} has failed CI {count} times. Stopping monitor — please investigate manually."
   d. If count <= 2: get the failed run ID with gh run list --branch {branch} --status failure --limit 1 --json databaseId --jq '.[0].databaseId', then read logs with gh run view <run-id> --log-failed. Diagnose and fix the issue if straightforward (test failures, lint errors, type errors, missing imports). Commit with message "fix(ci): <description>" and push to {branch}. If the failure is ambiguous or infrastructure-related, tell the user and wait for next cycle. Stop after pushing — next cycle will check results.

4. Merge readiness (all CI checks passed):
   a. If reviewDecision is CHANGES_REQUESTED: read review comments with gh api repos/:owner/:repo/pulls/{pr_number}/reviews. Address simple feedback (typos, naming, small fixes), commit and push. For substantive design disagreements, tell the user and wait.
   b. If reviewDecision is REVIEW_REQUIRED: tell the user approvals are needed (do this once — check if you already said this recently before repeating).
   c. If mergeable is CONFLICTING:
      Attempt rebase in a temporary worktree to avoid WSL file-locking:
        REBASE_DIR="${TMPDIR:-/tmp/claude-1000}/rebase-{pr_number}"
        git worktree add "$REBASE_DIR" {branch}
        cd "$REBASE_DIR"
        git rebase origin/{main_branch}
      If the rebase hits conflicts, check which files conflict:
        git diff --name-only --diff-filter=U
      - If the ONLY conflicting files are .ipynb notebooks: take the base branch version for each (git checkout origin/{main_branch} -- <file>), then git add <file> and git rebase --continue. Notebooks are JSON blobs that cannot be meaningfully merged — their outputs are regenerable. Tell the user which notebooks were reset.
      - For trivial non-notebook conflicts (import ordering, whitespace): resolve, git add, and git rebase --continue.
      - For ambiguous conflicts: git rebase --abort, tell the user, and wait. Do NOT retry on the next cycle — escalate immediately.
      After successful rebase:
        git push --force-with-lease
        cd -
        git worktree remove "$REBASE_DIR"
   d. If mergeable is UNKNOWN: wait for next cycle.

   e. If reviewDecision is any other unexpected value: tell the user
      about the review state and wait for next cycle.

5. All clear (reviewDecision is APPROVED or empty, mergeable is MERGEABLE):

   a. Bot review triage gate (run before every merge attempt):
      First, count prior fix(review) attempts: git log --oneline --grep="fix(review):" origin/{main_branch}..origin/{branch} | wc -l
      If count > 6: cancel this cron job (CronDelete job {cron_job_id}). Tell the user: "PR #{pr_number} has had {count} review fix attempts. Stopping monitor — please address review comments manually." Stop.

      Check for the most recent fix(review) commit timestamp (in UTC):
      git log --format="%aI" --grep="fix(review):" origin/{main_branch}..origin/{branch} | head -1
      If a fix(review) commit exists, convert it to UTC and record as LAST_FIX_TIME. Note: git returns local timezone (%aI) while GitHub API returns UTC — normalize both to UTC before comparing.

      Fetch inline review comments (these capture CodeRabbit/Copilot line-level findings):
      gh api repos/:owner/:repo/pulls/{pr_number}/comments --paginate --jq '[.[] | {user: .user.login, body: .body, path: .path, created_at: .created_at}]'

      Discard stale comments using two filters:
      a. If LAST_FIX_TIME is set, discard any comments with created_at <= LAST_FIX_TIME — those were already addressed by the fix commit.
      b. Check if the base branch was updated since the comment was posted: get the most recent merge commit on {main_branch} with `gh api repos/:owner/:repo/commits?sha={main_branch}&per_page=1 --jq '.[0].commit.committer.date'`. Discard any bot comments with created_at before this timestamp — they were written against a now-outdated base and may reference code that has since changed. Note: normalize both timestamps to UTC before comparing. Caveat: this filter is intentionally coarse — it may discard comments that are still relevant if main was updated by an unrelated PR. This tradeoff is acceptable because false negatives (skipping a valid comment) are recoverable on the next cycle, while false positives (endlessly fixing stale comments) cause infinite fix loops.

      Triage remaining comments: classify as actionable (bug report, crash scenario, missing validation, wrong logic, type error) or non-actionable (style suggestion, praise, summary walkthrough, question already answered by the code).
      - If ANY actionable comments exist: address at most 5 per cycle, prioritizing by severity (crashes > wrong logic > missing validation > type errors). Commit with message "fix(review): <description>", push to {branch}. Say "PR #{pr_number}: addressed review comments, waiting for re-review." Stop — next cycle will re-check after bots re-review.
      - If no actionable comments remain (all non-actionable or empty): proceed to merge.

   b. Merge:
      gh pr merge {pr_number} {merge_strategy} --delete-branch
   - On success: cancel this cron job (CronDelete job {cron_job_id}). Say "PR #{pr_number} merged successfully."
     Then clean up:
     c. Ensure CWD is the main repo root (not inside a worktree): get the main worktree path from git worktree list (the first entry is always the main worktree) and cd there. Do NOT use git rev-parse --show-toplevel — it returns the current worktree's root, not the main repo's.
        Remove the worktree (if path is not "none") with git worktree remove --force {worktree_path}, then delete the local branch with git branch -d {branch}. If -d fails (branch not fully merged into current HEAD), use git branch -D {branch} — this is safe because the PR was just merged on the remote.
     d. If {remote_url_switched} is "true", restore the original remote URL: git remote set-url origin {original_remote_url}
     e. Run git pull origin {main_branch}. If it fails due to uncommitted local changes, report the error — do not stash automatically.
     f. If {plan_file} is not "none": update the current phase to MERGED with the PR URL in {plan_file}, then check remaining TODO phases: TODO_COUNT=$(grep -c "| TODO |" "{plan_file}" || echo "0"). If TODO_COUNT is 0, rename the plan: git mv "{plan_file}" "{plan_file%.md}-done.md" 2>/dev/null || mv "{plan_file}" "{plan_file%.md}-done.md" && git commit -m "mark plan complete". Inform the user of remaining phases or completion. If {plan_file} is "none", skip plan updates.
     g. Clean up state: rm .workflow-state.json
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
- **Bot reviewers post comments without setting reviewDecision**: The
  cron prompt fetches and triages inline review comments (step 5a)
  before every merge attempt. This catches CodeRabbit, Copilot, and
  similar automated reviewers. Comments older than the most recent
  fix(review): commit are ignored to prevent infinite fix loops.

## Common Mistakes

- Starting monitoring before the PR exists
- Not cancelling the cron job after merge (leads to error noise)
- Force-pushing to fix CI instead of creating new commits
- Amending commits instead of creating separate fix commits
- Repeatedly notifying the user about pending approvals every cycle
- Attempting to fix flaky/infrastructure CI failures with code changes
- Not checking for existing monitors before creating a duplicate

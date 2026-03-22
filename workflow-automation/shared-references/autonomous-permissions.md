# Autonomous Permissions Pre-flight

This protocol verifies the session has permissions and sandbox
configuration needed for autonomous operation (used by auto-implement).

## Pre-flight Checks

### a. Check sandbox prerequisites

1. Verify `.claude/commands/` exists. If missing, create it:
   `mkdir -p .claude/commands`
   (The sandbox requires this directory to exist — without it, all
   git and gh commands are blocked.)
2. Read the permissions template from
   `permissions-template.json` (in this directory). This template
   contains the baseline permissions and sandbox configuration needed
   for autonomous operation.
3. Check `.claude/settings.local.json` exists and contains **at least**
   every entry from the template's `permissions.allow` list and the
   `sandbox` block. The user may have added project-specific entries
   (e.g., `Bash(pytest:*)`, `Bash(npm test:*)`) — those are fine. Only
   flag entries that are **missing** from the template baseline.

### b. Detect plan language requirements

If a plan file exists, scan it for language-specific tools the
implementation will need. Check for references to:

| Indicator in plan | Command to verify |
|---|---|
| R, Rscript, testthat, devtools, CRAN | `Rscript --version` |
| Python, pytest, pip, conda | `python3 --version` |
| Node, npm, yarn, jest, vitest | `node --version` |
| Rust, cargo | `cargo --version` |
| Go | `go version` |

For each detected language, run the corresponding version command.
These commands are auto-approved by the sandbox
(`autoAllowBashIfSandboxed: true`) — no granular permission entries
are needed. This step only verifies the interpreter is **installed and
available** on the system. If any command fails (not found), stop and
tell the user which tool is missing before starting the autonomous run.

Skip this step if no plan file exists yet (the plan skill will run
first, and auto-implement re-checks on resume).

### c. Run permission test commands

1. `git status` — tests Bash(git:*) permission
2. `gh pr list --limit 1 --state closed` — tests Bash(gh:*) permission
3. Read the plan file or `CLAUDE.md` — tests Read permission
4. `echo "preflight" > /dev/null` — tests general Bash permission
5. Language-specific commands from Step b (if any were detected)

### d. Failure message

If **any command triggers a user approval prompt**, **the sandbox
blocks a command**, or **the settings file is missing template
entries**, stop and print:

> **Autonomous mode requires sandbox configuration.**
>
> 1. Create the commands directory if it doesn't exist:
>    `mkdir -p .claude/commands`
>
> 2. Copy the permissions template to your project:
>    `cp <plugin-path>/shared-references/permissions-template.json .claude/settings.local.json`
>
> The `sandbox` block is what makes autonomous runs work:
> - `enabled: true` restricts file writes to the project directory
> - `autoAllowBashIfSandboxed: true` auto-approves all bash commands
>   within that sandbox — no per-command permission entries needed
> - `excludedCommands: ["git", "gh"]` exempts git/gh from sandbox
>   restrictions so `.git/` writes succeed
>
> Language tools (R, Python, Node, etc.) do **not** need explicit
> permission entries — the sandbox auto-approves them. They only need
> to be installed on the system. Then re-invoke `/auto-implement`.

Only proceed when all test commands pass without prompts.

## Required Configuration

For autonomous operation without approval prompts, the project needs:

1. **`.claude/commands/` directory** — must exist (even if empty).
   The sandbox checks for this directory; without it, git and gh
   commands are blocked.

2. **`.claude/settings.local.json`** with the sandbox block from
   the permissions template:
   `cp <plugin-path>/shared-references/permissions-template.json .claude/settings.local.json`

   `CronCreate`, `CronDelete`, `CronList`, and `Agent` do not
   require explicit permission entries.

The `sandbox` block is the key to zero-prompt autonomous runs:
- `enabled: true` restricts file writes to the project directory
- `autoAllowBashIfSandboxed: true` auto-approves **all** bash
  commands within that sandbox — no per-language or per-tool
  permission entries needed (R, Python, Node, test runners, etc.
  are all covered)
- `excludedCommands: ["git", "gh"]` exempts git and gh from sandbox
  restrictions — without this, the sandbox denies writes to `.git/`
  internals and every git command falls back to
  `dangerouslyDisableSandbox`

Note: The template includes granular `Bash(git:*)` etc. entries as
a fallback for when sandbox is disabled. With sandbox enabled, they
are redundant — `autoAllowBashIfSandboxed` covers everything.

If permissions are not configured, the skill still works but will
pause for user approval on each tool call — defeating the purpose
of autonomous mode.

## Never bypass the sandbox

During autonomous runs, **never use `dangerouslyDisableSandbox: true`**
for language or test commands (R, Python, Node, etc.). If the sandbox
blocks a command, this indicates a configuration issue — not a reason
to bypass sandbox protections.

Common cause: **worktrees outside the project directory**. When a
worktree is created at `../feat-something/`, it falls outside the
sandbox's allowed write paths. Commands run from there hit sandbox
restrictions, and Claude's default behavior is to retry with
`dangerouslyDisableSandbox: true` — which then requires explicit
per-command permission entries that don't exist for language tools.

**Prevention**: The implement skill's branching strategy should prefer
creating worktrees **inside** the project directory or fall back to a
regular branch in the current repo (which stays within the sandbox).
If a sandbox restriction is hit during an autonomous run:
1. Do NOT retry with `dangerouslyDisableSandbox`
2. Fall back to a regular branch in the current repo
3. Log the issue for the user

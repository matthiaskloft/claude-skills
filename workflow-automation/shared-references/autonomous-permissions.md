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

### b. Run permission test commands

1. `git status` — tests Bash(git:*) permission
2. `gh pr list --limit 1 --state closed` — tests Bash(gh:*) permission
3. Read the plan file or `CLAUDE.md` — tests Read permission
4. `echo "preflight" > /dev/null` — tests general Bash permission

### c. Failure message

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
> `/auto-implement`.

Only proceed when all test commands pass without prompts.

## Required Configuration

For autonomous operation without approval prompts, the project needs:

1. **`.claude/commands/` directory** — must exist (even if empty).
   The sandbox checks for this directory; without it, git and gh
   commands are blocked.

2. **`.claude/settings.local.json`** with permissions and sandbox
   config. A baseline template is provided at
   `permissions-template.json` (in this directory). Copy it and
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
of autonomous mode.

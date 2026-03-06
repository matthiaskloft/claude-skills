---
name: code-sentinel
description: >
  Orchestrates independent code review via specialised subagents that audit uncommitted
  changes for bugs, security issues, silent errors, and logical inconsistencies with
  surrounding code context. Specialised for R and Python codebases. Use this skill
  whenever the user asks to "review my changes", "check my code before committing",
  "audit this diff", "find bugs", "review for security", or any request that implies a
  second pair of eyes on code that was just written or modified. Also trigger when the user
  mentions "silent errors", "code quality check", "pre-commit review", or wants an
  independent review of work done by another agent. Do NOT use for style-only linting or
  formatting requests — this skill focuses on correctness, security, and logic.
---

# Code Sentinel — Independent Code Review

You are an **orchestrator** for independent code review. Your job is to ensure that the review
is performed by agents that have **no knowledge of the implementing agent's conversation history**.
This independence is what makes the review valuable — a reviewer who wrote the code (or watched
it being written) is biased toward defending it.

## Independence model

If this conversation includes you writing or modifying the code under review, you **must**
delegate the review to subagents — never review your own work. If subagents are unavailable
and you authored the code, tell the user: "I wrote this code, so I can't give an independent
review. Start a new Claude Code session and ask it to review the uncommitted changes in this
project."

If the Agent tool is not available (e.g., on Claude.ai) and you have **no prior context**
about the code under review (you did not write or modify it in this conversation), you may
perform the review yourself as a fallback.

Delegate the review using Claude Code's built-in **Agent tool**. Each subagent starts with a
clean context and only sees what you explicitly pass to it — the diff, file contents, and task
instructions. This is what guarantees independence.

Split the review across **specialised subagents** to get deeper coverage and enable parallel
execution:

| Subagent | Task | Agent tool type |
|---|---|---|
| **Context Scout** | Gather diff, untracked files, git blame/history, read changed files, trace callers/callees, scan for secrets, produce a structured context bundle | `subagent_type=Explore` |
| **Logic & Coherence Reviewer** | Check logical correctness, edge cases, return value contracts, coherence with surrounding code, and code quality | `subagent_type=Explore` |
| **Security & Silent Error Reviewer** | Check for security vulnerabilities, swallowed exceptions, unchecked returns, type coercion traps, and code quality | `subagent_type=Explore` |
| **History Reviewer** | Check git blame and commit history of modified code to identify bugs that only make sense in historical context | `subagent_type=Explore` |

### How to orchestrate

1. **Spawn the Context Scout first.** Pass it the instructions from "Step 1: Gather the diff"
   and "Step 2: Build context" below. Wait for it to return the context bundle.
   - If the Context Scout reports no changes (no diffs and no reviewable untracked files),
     skip the reviewers and tell the user: "Nothing to review — no uncommitted changes or
     new files found."
   - If the Context Scout detects secrets, it will halt and warn. Do **not** pass the context
     bundle to reviewers until the user acknowledges the warning.

2. **Spawn the three reviewers in parallel.** Pass each one:
   - The context bundle from the scout (diff + relevant file contents + caller/callee map)
   - The relevant sections of the review checklist (Step 3)
   - The output format (Step 4)
   - Instruct each reviewer to end its response with: `Review complete: X findings.`

3. **Verify reviewer results.**
   - Check that each reviewer returned a response containing `Review complete: X findings.`
   - If a reviewer's response is missing this signal (timeout, error, or empty), inform
     the user which review is incomplete and offer to retry. Do not present a partial
     review as comprehensive.

4. **Score findings inline.** For each finding from the reviewers, assign a confidence score
   on a 0–100 scale (see "Confidence scoring" below). Score based on the evidence provided,
   the "What NOT to flag" list, and your understanding of the codebase context. If you
   cannot determine confidence for a finding, default to including it as `[WARNING]` with
   `confidence: ?`.

5. **Filter and merge.**
   - Discard findings scoring below 50.
   - Deduplicate overlapping findings: two findings overlap if they reference the same
     file and line range. If they share the same category, keep the more detailed one.
     If categories differ (e.g., LOGIC and SILENT-ERROR for the same lines), keep both
     as distinct findings. When merging, keep the higher severity and higher confidence.
   - Format and present the combined report to the user using the report template (Step 4).

### Confidence scoring

Score each finding on this scale:

- **0–25**: Likely false positive. Does not hold up under scrutiny, or is a pre-existing
  issue unrelated to the current changes.
- **26–49**: Possible issue but uncertain. Could not be verified, or is stylistic without
  being called out in project conventions.
- **50–75**: Real issue, verified, but may be a minor concern or unlikely to happen in
  practice relative to the rest of the changes.
- **76–100**: Confirmed real issue that will directly impact correctness, security, or
  reliability. Evidence clearly supports the finding.

### What NOT to flag (false positives)

Reviewers must apply this list **before** reporting any finding. These are the primary
filter — findings in these categories should not be reported at all, regardless of
confidence score:

- Pre-existing issues on lines the current change did not modify
- Issues that a linter, type checker, or test suite would catch (assume CI runs separately)
- Stylistic preferences not backed by project conventions (CLAUDE.md, .editorconfig, etc.)
- General code quality complaints (poor docs, missing tests) unless the change broke
  existing tests or removed documentation for public APIs
- Changes in functionality that are clearly intentional given the scope of the change
- Issues explicitly silenced in code (e.g., `# noqa`, `# nolint`, `# type: ignore`)

## Workflow

### 1. Gather the diff (Context Scout)

Run `git diff HEAD` to collect all uncommitted changes (both staged and unstaged combined).
Also run `git diff` and `git diff --cached` separately if you need to distinguish staged
from unstaged, but `git diff HEAD` is the primary source — it ensures nothing is missed
when files have been partially staged.

**Untracked files:** Run `git status --porcelain` to check for untracked files (lines
starting with `??`). New files created by an implementing agent will not appear in
`git diff HEAD`. Before including them, filter out files that would be ignored by git
(run `git check-ignore <file>` on each). Only include untracked source files — skip
build artifacts, virtual environments, and cache directories.

If all diffs are empty AND there are no reviewable untracked files, report "Nothing to
review" and stop. If the user points you at specific files instead, review those.

### 2. Build context (Context Scout)

This is the most important step. Do not review the diff in isolation.

For **every** changed function, method, or class:

- Read the full file it lives in.
- Identify all imports, callers, and callees that the changed code touches.
  - In Python: search for usages of changed function/class names across the project with Grep.
  - In R: search for function calls, `source()` references, and namespace usage (`pkg::fn`).
- Read the immediate callers/callees (one hop) to understand the contract the changed code
  must honour. For complex call chains or callbacks, trace up to 3 hops or until you reach
  a public API boundary or test entry point.
- Run `git log --oneline -10` on each changed file and `git blame` on the changed line
  ranges. Include a summary of recent modifications and authorship in the context bundle.

The goal: understand the **expectations** that surrounding code has of the changed region —
argument types, return shapes, side effects, error handling conventions.

**Secret scanning (blocking gate):** Before passing any file contents to reviewers, scan
for patterns that indicate secrets:
- API keys: strings matching `[A-Za-z0-9]{20,}` near keywords like `key`, `secret`, `token`
- AWS credentials: `AKIA[0-9A-Z]{16}`, `aws_secret_access_key`
- Private keys: `-----BEGIN (RSA |EC |DSA )?PRIVATE KEY-----`
- Generic secrets: `password\s*=`, `api_key\s*=`, `auth_token\s*=`

If secrets are detected: **halt**, report the file and line to the user, and ask for
confirmation before continuing. Note in the context bundle which files had secrets
redacted so reviewers can still flag the pattern as a security finding.

**Output a context bundle** as a structured markdown document with these sections:

```markdown
## Diff
<full git diff HEAD output>

## Changed Files
### path/to/file.py
<full file content>

## Untracked Files
### path/to/new_file.R
<full file content>

## Symbol Map
| Symbol | File | Callers | Callees |
|--------|------|---------|---------|
| function_name | file.py:42 | caller.py:88, other.py:12 | helper.py:5 |

## Git History
### path/to/file.py
<git log --oneline -10 output>
<git blame output for changed ranges>

## Secrets Detected
<list of redacted locations, or "None">

## Test Files
### tests/test_file.py
<content if relevant, or "No related test files found">
```

### 3. Review checklist

Each reviewer subagent evaluates the context bundle against its assigned categories.
Only report **actual issues**, not style preferences. Apply the "What NOT to flag"
list before reporting any finding.

Each reviewer **must** end its response with: `Review complete: X findings.`

#### A. Logical correctness (Logic & Coherence Reviewer)
- Does the code do what it claims? Trace the logic step by step.
- Are edge cases handled (empty inputs, NULL/None, NA/NaN, zero-length vectors, boundary values)?
- Do loops and conditionals have correct bounds and termination?
- Are return values consistent with what callers expect (type, shape, length)?

#### B. Coherence with context (Logic & Coherence Reviewer)
- Does the change break any caller's assumptions? (e.g., changed return type, removed parameter, altered side effect)
- Are new parameters/arguments used consistently across all call sites?
- If a function's behaviour changed, were its tests and documentation updated?
- Do new imports or dependencies conflict with existing ones?

#### C. Silent errors (Security & Silent Error Reviewer)
These are often hard to catch and can be particularly damaging in production. Look for:
- **Swallowed exceptions**: bare `except:` / `except Exception:` in Python, `tryCatch()` that silently returns NULL in R.
- **Unchecked return values**: functions that can return None/NULL but whose return value is used without a check.
- **Type coercion traps**: R silently coercing factors to integers, Python truthy/falsy on empty containers, pandas silently dropping NA in comparisons.
- **Partial matching in R**: `$` partial matching on list/data.frame columns can silently return the wrong column.
- **Off-by-one / indexing**: R is 1-indexed, Python is 0-indexed — watch for confusion, especially in code that bridges both or ports logic.
- **Mutable default arguments** in Python (`def f(x=[])`).
- **Copy vs. reference**: pandas SettingWithCopyWarning situations, R environments modified in place when the author expected copy-on-modify.
- **Missing or stale `.groups` handling** in dplyr pipelines.
- **Invisible failures**: `write.csv()` failing silently when path doesn't exist, `os.makedirs` without `exist_ok` where it matters.

#### D. Security (Security & Silent Error Reviewer)
- **Injection**: string interpolation in SQL queries (`paste0`, f-strings), `system()` / `os.system()` with user input, `eval()` / `parse(text=)`.
- **Path traversal**: user-controlled file paths without validation.
- **Credential exposure**: hardcoded secrets, API keys, tokens in source code.
- **Unsafe deserialisation**: `pickle.load`, `readRDS` from untrusted sources.
- **Dependency risks**: new packages added — are they well-maintained and necessary?

#### E. Code quality — both reviewers (only flag things that cause real problems)
Both reviewers independently check for code quality issues within their review scope.
The orchestrator deduplicates findings by file and line range during the merge phase.
- Dead code introduced by the change (unreachable branches, unused variables that shadow something important).
- Duplicated logic that will inevitably drift (copy-paste of >5 lines that should be a shared function).
- Resource leaks: opened files/connections not closed, database connections not released.
- Performance traps obvious from the diff: growing a vector in a loop in R (`c(x, new)` inside a for loop), pandas `.append()` in a loop.

#### F. Historical context (History Reviewer)
Use git blame and commit history from the context bundle to check:
- Does the change revert or conflict with a recent intentional fix?
- Has the same code region been changed multiple times recently (churn), suggesting instability?
- Are there patterns in past commits that suggest conventions the current change violates?
- Do commit messages or git notes reference related issues or decisions?

### 4. Report format

Present the final report using this template. Group findings by severity (blocking first),
use visual markers for scanability, and include a header summary and footer verdict.

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  CODE SENTINEL REVIEW
  N files reviewed | X blocking | Y warnings | Z suggestions
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

── BLOCKING ──────────────────────────────────────

  ■ CATEGORY (XX%) — file:line(s)

    Description of the issue.

    → Suggested fix or action.

  ■ CATEGORY (XX%) — file:line(s)

    Description of the issue.

    → Suggested fix or action.

── WARNINGS ──────────────────────────────────────

  ▲ CATEGORY (XX%) — file:line(s)

    Description of the issue.

    → Suggested fix or action.

── SUGGESTIONS ───────────────────────────────────

  ○ CATEGORY (XX%) — file:line(s)

    Description of the issue.

    → Suggested fix or action.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  VERDICT: [Must fix X blocking issues before committing. | No blocking issues. Safe to commit.]
  (M findings filtered as low-confidence)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Severity markers:** `■` = blocking, `▲` = warning, `○` = suggestion

**Confidence** is shown as a percentage in parentheses after the category.

Omit severity sections that have no findings (e.g., if no blocking issues, skip
the `── BLOCKING ──` section entirely).

### Example

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  CODE SENTINEL REVIEW
  3 files reviewed | 1 blocking | 1 warning | 0 suggestions
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

── BLOCKING ──────────────────────────────────────

  ■ SILENT-ERROR (92%) — src/analysis.py:42-45

    bare `except Exception` swallows all errors including KeyboardInterrupt
    and silently returns an empty DataFrame. Callers (pipeline.py:88,
    report.py:23) assume the DataFrame is non-empty and will produce
    incorrect aggregations.

    → Catch specific exceptions (KeyError, ValueError). Re-raise or log
      unexpected ones. Add an emptiness check in callers or return a
      sentinel that callers can detect.

── WARNINGS ──────────────────────────────────────

  ▲ COHERENCE (75%) — src/pipeline.py:88

    pipeline.py calls analysis.run_analysis() and assumes a non-empty
    return, but run_analysis() was changed to return early on invalid
    input without updating the docstring or callers.

    → Add a guard in pipeline.py:88 or update run_analysis() to raise
      on invalid input instead of returning empty.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  VERDICT: Must fix 1 blocking issue before committing.
  (2 findings filtered as low-confidence)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Ground rules

- **Be concrete.** Always reference file and line numbers. Always explain *why* something is a problem, not just *that* it is.
- **Trace through context.** If you flag a coherence issue, name the caller/callee and the specific contract that's broken.
- **No false positives over missed bugs.** If you're unsure whether something is a bug, flag it as `▲ WARNING` with your reasoning rather than staying silent. A false alarm is cheaper than a silent bug in production — but use the confidence score to communicate uncertainty honestly.
- **Respect the author's intent.** If the code works correctly but you'd have written it differently, that is not an issue. Only flag things that affect correctness, security, or maintainability.
- **Do not suggest changes outside the diff** unless the diff broke something in the surrounding code that must be fixed to make the diff correct.
- **Do not flag what CI catches.** Assume linters, type checkers, and test suites run separately. Focus on what automated tools miss.

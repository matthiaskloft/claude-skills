---
name: plan
description: >
  Create a structured feature plan document before implementation. Use when the
  user says "plan a feature", "design this", "create a plan", "let's plan",
  "write a plan for", "think through how to build", "architect this",
  "how should I approach building", or describes a feature they want to build
  and needs a design-first approach. Also trigger when the user says "/plan".
  Do NOT use for tasks small enough to implement directly without planning.
  Do NOT activate if the user is mid-implementation working from an existing plan.
---

# Plan Phase — Feature Design Document

You are creating a **plan document** that captures the design decisions,
scope, and implementation steps for a feature before any code is written.

## When to Plan vs. Just Do It

- **Plan**: Multi-file changes, new abstractions, architecture decisions,
  anything the user explicitly asks to plan
- **Just do it**: Single-file fixes, small additions, clear-cut changes

If the task is too small for a plan, tell the user and offer to implement
directly.

## Step-by-Step

### 1. Understand the Request

Before writing anything, gather context:
- Read CLAUDE.md for project conventions and dev doc locations
- Read relevant existing code to understand the current architecture
- Identify the language/framework and its conventions
- Look for existing spec docs (`spec-*.md`) in the dev docs directory
  and the project root. If a spec exists for the requested feature, use
  it as the primary source for the plan's Summary, Design Decisions, and
  Scope sections. Do not re-derive design decisions that the spec already
  resolved — treat those as settled. Only ask clarifying questions about
  implementation phasing, not about design choices already documented in
  the spec.
- Ask clarifying questions if the scope is ambiguous
- Identify constraints (backwards compatibility, performance, dependencies)

For ambiguous or large-scope requests where the design approach is
unclear, suggest using the **brainstorm** skill first to explore the
problem space and produce a spec doc before committing to a plan.

### 2. Create the Plan Document

- Check the project's CLAUDE.md for where development docs are stored
  (e.g., `dev/`, `docs/dev/`, `docs/`). Place the plan in a `plans/`
  subfolder there, creating it if needed.
- If no convention is found, place the plan in the project root.
- Filename: `plan-<kebab-case-name>.md`
  - When a plan is fully completed (all phases merged), it gets renamed
    to `plan-<kebab-case-name>-done.md` — see the ship and
    implement-ship-all skills for when this happens.
- Use the template in `references/plan-template.md`
- For a filled-in example, see `references/plan-example.md`
- Fill in every section — leave nothing as placeholder text

Key sections to get right:
- **Summary**: One paragraph on motivation + outcome. Be specific.
- **Design Decisions**: Document alternatives considered, not just the choice
- **Scope**: Explicitly list what's out of scope to prevent creep. Document
  out-of-scope items that still need doing in a todo file in the project's
  development docs directory (e.g., `dev/todos.md`), creating it if needed.
- **Implementation Plan**: Break into phases. Each phase should be
  independently shippable if possible and small enough to complete in a
  single session of agentic coding (one `/implement` invocation or one
  focused Claude Code conversation). A phase is independently shippable
  if it can be merged without breaking existing functionality or leaving
  dead code paths — no feature flags or temporary scaffolding needed.
- **Verification**: How to confirm correctness beyond "tests pass". Align
  with the project's review conventions if a review checklist exists.

### 3. Independent Plan Review (Iterative)

Review the plan in a loop until no new issues are found:

**Review loop:**

1. Spawn a review agent using the Agent tool
   (`subagent_type="feature-dev:code-architect"`) with this focus prompt:
   "Review this feature plan against the existing codebase. Verify:
   (1) feasibility — do the referenced files, APIs, and patterns exist,
   (2) gaps — are there missing phases, dependencies, or edge cases,
   (3) risks — could any phase break existing functionality,
   (4) scope — is each phase independently shippable.
   Cross-check any enum values, parameter names, and framework-specific
   constants mentioned in the plan against actual codebase definitions —
   verify against validators and class constructors.
   For each finding, state severity (blocker/warning/suggestion)
   and a concrete recommendation. End with: Review complete: X findings
   (Y blockers, Z warnings)."
   Use the default model — architectural reasoning requires deep context.
   - Pass the plan document and any relevant source files the plan references
   - Wait for the reviewer to return

2. Handle feedback:
   - **Blockers**: Revise the plan to address every blocker. If a blocker
     requires a user decision (e.g., ambiguous scope, conflicting
     constraints), use AskUserQuestion to present the options with
     descriptions rather than plain text questions.
   - **Warnings**: Evaluate each warning — revise the plan if warranted,
     otherwise note it in the plan's "Review Feedback" section
   - **Suggestions**: Include in the plan's "Review Feedback" section for
     the user to see

3. If any revisions were made in step 2, repeat the review loop: re-run
   step 1 on the updated plan. Prepend the reviewer prompt with: "This is
   iteration N. Changes since last review: [list the specific sections
   revised and what changed]." This helps the reviewer focus on the changes
   and avoid re-raising already-addressed issues.

4. Stop when **no revisions were made in step 2** — i.e., all blockers have
   been addressed, all warnings have been either addressed or noted without
   requiring changes, and only suggestions (or no findings) remain.

5. Record the iteration count in the plan's "Review Feedback" section
   (e.g., "Reviewed in 2 iterations") so the user can gauge how contested
   the plan was.

**Guard rail**: Cap the loop at 4 total review iterations. If the 4th
review still returns blockers that would require more revisions, stop
there, present the plan with those unresolved issues clearly flagged,
and ask the user for guidance instead of starting a 5th cycle.

**Fallback**: If the Agent tool is unavailable, note in the plan that it
was not independently reviewed and present it directly to the user.

### 4. Present for Review

Show the user the completed plan and ask for approval before moving to
implementation. Highlight:
- Key design decisions that could go either way
- Scope boundaries they might want to adjust
- Risks or unknowns

### 5. Track Status

Every plan has a status table at the top:

| Phase | Status | Date | Notes |
|-------|--------|------|-------|
| Plan | DONE | 2026-03-10 | Approved |
| Phase 1: Core | TODO | | |
| Phase 2: Extensions | TODO | | |
| Ship | TODO | | |

Statuses: `TODO`, `IN_PROGRESS`, `DONE`, `IMPLEMENTED`, `COMMITTED`, `MERGED`, `SKIPPED`

## After Planning

Once approved, the user can proceed with the **implement** skill to build
the feature from the plan, or implement it directly in the current session.

## Common Mistakes

- Writing a plan that's just a task list (missing the *why* and *design decisions*)
- Over-scoping: trying to plan everything at once instead of phasing
- Under-specifying verification: "write tests" is not a verification plan
- Not reading existing code before planning (leads to designs that fight the codebase)
- Bad phase split: "Phase 1: all the code, Phase 2: all the tests" — tests
  should be part of each phase, not a separate phase
- Phases with hidden dependencies: Phase 2 assumes Phase 1 created a helper
  function but doesn't say so — each phase must list what it depends on

## Handling Edge Cases

- **Plan is too big**: If the feature requires more than 4-5 phases, suggest
  splitting it into separate features with their own plans.
- **User rejects the plan**: Ask what they'd change — adjust scope, rethink
  design decisions, or offer to skip planning and implement directly.
- **Reviewer finds blockers**: The iterative review loop (Step 3) handles
  this automatically. If blockers persist after 4 iterations, present the
  plan with unresolved issues flagged and ask for user guidance.
- **Ambiguous request**: If the user says "just plan it" without answering
  clarifying questions, make reasonable assumptions and document them
  explicitly in the plan's Notes section.

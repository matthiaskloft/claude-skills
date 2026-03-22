---
name: feature-spec
description: >
  Explore a feature idea and produce a spec doc before planning. Use when
  the user says "feature-spec", "explore this idea", "let's discuss the
  approach", "what are my options for", or wants to think through a
  design before committing to a plan. Also trigger when the user says
  "/feature-spec". Do NOT use for tasks that already have a clear design
  — use the feature-plan skill directly. Do NOT use mid-implementation.
---

# Feature Spec — Design Exploration to Spec

This skill produces the **Spec** section of a plan document — the
design, requirements, and decisions for a feature. It does NOT produce
implementation phases. After the feature-spec skill, use the **feature-plan**
skill (`/feature-plan`) to add phased implementation steps, or **auto-implement**
(`/auto-implement`) to plan and ship in one flow.

**Brainstorm = "what and why"** (Spec section of the plan).
**Plan = "how and when"** (Implementation Plan section).

## Step-by-Step

### 1. Explore Project Context

Before asking questions, understand the landscape:
- Read CLAUDE.md for project conventions, architecture, and constraints
- Read relevant existing code to understand what already exists
- Check recent commits for ongoing work that might relate
- Identify the language/framework and its conventions

### 2. Present the Decision Landscape

Before diving into questions, give the user a concise overview of what
you found and what needs to be decided. Output a short message (not a
tool call) covering:

- **Context summary**: What exists today — relevant code, patterns,
  and constraints you discovered in Step 1 (2-4 bullet points)
- **Key decisions ahead**: The major design questions this feature spec
  will need to resolve, presented as a numbered list (typically 3-6
  items). Each item should be a concrete question, not a vague topic.
  Examples: "Where should the new endpoint live — extend the existing
  controller or create a new one?", "Which serialization format —
  JSON, Protobuf, or both?"
- **Rough flow**: A one-sentence note on the order you plan to tackle
  these decisions (e.g., "I'll start with scope and requirements, then
  move to architecture choices")

This gives the user a mental map of the feature spec before the first
question arrives. Keep it brief — aim for 8-15 lines total. Do not
use AskUserQuestion for this step; just present the overview as text.

### 3. Ask Clarifying Questions

Use **AskUserQuestion** as the default interaction tool — one question
at a time, prefer multiple choice with descriptions.

**Before every question**, output a brief context summary as plain text
(not inside AskUserQuestion). This keeps the user oriented as the
interview progresses. The summary should include:
- **Where we are**: Which decision area this question addresses (refer
  back to the numbered decisions from Step 2)
- **What we've established**: 1-2 sentences recapping relevant answers
  so far that inform this question (skip for the first question)
- **Why this matters**: One sentence on how this answer shapes the design

Keep the summary to 3-5 lines — enough to provide context, not so much
that it becomes a wall of text. Then immediately follow with the
AskUserQuestion call.

Focus on understanding:
- **Purpose**: What problem does this solve? Who benefits?
- **Constraints**: Performance requirements, backwards compatibility,
  dependencies, deadlines
- **Success criteria**: How will you know it works?
- **Users**: Who will use this? How?

Key principles:
- One question per message — do not overwhelm
- Prefer multiple choice (with descriptions) over open-ended questions
- If the user's answer raises new questions, ask those before moving on
- Be willing to go back and revisit earlier answers

### 4. Propose Approaches

When you understand the problem well enough, propose 2-3 approaches
using AskUserQuestion:
- Mark the recommended option with "(Recommended)" at the end of its
  label
- Each option should have a description explaining trade-offs
- Lead with the recommended approach and explain why in the question
  text
- Include enough detail that the user can make an informed choice

### 5. Refine the Design

Iterate on the chosen approach:
- Refine scope — what's in, what's out
- Identify risks and mitigation strategies
- Resolve open questions
- Continue using AskUserQuestion for decisions
- Apply YAGNI ruthlessly — remove unnecessary features from the design

### 6. Write the Spec

Write the Spec section into a plan document:

- **Location**: Check CLAUDE.md for a dev docs directory convention,
  look in its `plans/` subfolder. If no convention is found, use the
  project root.
- **Filename**: `plan-<kebab-case-name>.md`
- **Template**: Use the plan template from
  `../feature-plan/references/plan-template.md`. Fill in the `## Spec`
  section and its subsections. Leave the `## Implementation Plan`
  section with placeholder content — the feature-plan skill fills
  that in.
- **Status table**: Set `Spec` to `IN_PROGRESS`. Leave `Plan` and all
  phases as `TODO`.

**Spec subsections to fill in:**
- Summary (motivation + outcome)
- Requirements (what the feature must do — specific and testable)
- Design decisions (with alternatives considered and rationale)
- Scope (in scope / out of scope)
- Architecture overview (components, data flow, key interfaces)
- Constraints (performance, compatibility, dependencies)
- Open questions (anything unresolved)

### 7. Review the Spec

Run one automatic review after writing the spec — do not ask the user
whether to review.

1. Spawn a review agent using the Agent tool
   (`subagent_type="feature-dev:code-architect"`) with this focus prompt:
   "Review this spec (the `## Spec` section of the plan document)
   against the existing codebase. Verify:
   (1) feasibility — do the referenced APIs, patterns, and constraints
   hold in the current codebase,
   (2) completeness — are there missing requirements, edge cases, or
   architectural concerns,
   (3) consistency — do design decisions align with each other and with
   project conventions,
   (4) scope — is the scope clear and realistic, are in/out boundaries
   well-defined.
   For each finding, state severity (blocker/warning/suggestion) and a
   concrete recommendation. End with: Review complete: X findings
   (Y blockers, Z warnings)."
   - Pass the plan document and any relevant source files it references
   - Wait for the reviewer to return

2. Handle feedback:
   - **Blockers**: Revise the spec to address every blocker. If a
     blocker requires a user decision, use AskUserQuestion to present
     the options.
   - **Warnings**: Evaluate each warning — revise the spec if warranted,
     otherwise note it in the Open Questions section
   - **Suggestions**: Include in the Review Feedback section

3. After all blocker revisions are applied, mark `Spec` as `DONE` in
   the status table.

**Fallback**: If the Agent tool is unavailable, note in the Review
Feedback section that the spec was not independently reviewed and
present it directly.

### 8. Hand Off

Ask the user via AskUserQuestion whether to proceed:

> "Spec written and reviewed (`<path>`). What next?"

Options:
- "Yes, proceed to /feature-plan" — Create phased implementation plan
  from this spec
- "Plan and ship (/auto-implement)" — Plan, implement, and ship
  in one flow
- "Review spec first" — I want to review/edit the spec before planning
- "Done for now" — I'll plan later

If the user selects "Yes, proceed to /feature-plan", immediately invoke
the **feature-plan** skill (via the Skill tool) with the spec doc path as context,
noting that design decisions are already resolved in the spec.

If the user selects "Plan and ship", immediately invoke the
**auto-implement** skill (via the Skill tool) with the spec doc
path as context.

## Hard Gate

Do NOT write code during the feature-spec skill. This skill produces a spec,
not implementation. If the user asks to start coding, suggest completing
the feature spec first, then using `/feature-plan` followed by `/implement`.

## Common Mistakes

- Asking multiple questions in one message (one at a time)
- Using plain text questions instead of AskUserQuestion
- Jumping to implementation before the design is agreed
- Over-designing: adding features nobody asked for (YAGNI)
- Not exploring alternatives: settling on the first approach
- Writing a separate `spec-*.md` file instead of the plan document

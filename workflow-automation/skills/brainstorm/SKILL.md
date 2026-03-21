---
name: brainstorm
description: >
  Explore a feature idea and produce a spec doc before planning. Use when
  the user says "brainstorm", "explore this idea", "let's discuss the
  approach", "what are my options for", or wants to think through a
  design before committing to a plan. Also trigger when the user says
  "/brainstorm". Do NOT use for tasks that already have a clear design
  — use the plan skill directly. Do NOT use mid-implementation.
---

# Brainstorm — Design Exploration to Spec Doc

This skill produces a **spec doc** — the design, requirements, and
decisions for a feature. It does NOT produce an implementation plan.
After brainstorming, use the **plan** skill (`/plan`) to turn the spec
into a phased operational plan.

**Brainstorm = "what and why"** (spec doc).
**Plan = "how and when"** (phased implementation).

## Step-by-Step

### 1. Explore Project Context

Before asking questions, understand the landscape:
- Read CLAUDE.md for project conventions, architecture, and constraints
- Read relevant existing code to understand what already exists
- Check recent commits for ongoing work that might relate
- Identify the language/framework and its conventions

### 2. Ask Clarifying Questions

Use **AskUserQuestion** as the default interaction tool — one question
at a time, prefer multiple choice with descriptions.

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

### 3. Propose Approaches

When you understand the problem well enough, propose 2-3 approaches
using AskUserQuestion:
- Mark the recommended option with "(Recommended)" at the end of its
  label
- Each option should have a description explaining trade-offs
- Lead with the recommended approach and explain why in the question
  text
- Include enough detail that the user can make an informed choice

### 4. Refine the Design

Iterate on the chosen approach:
- Refine scope — what's in, what's out
- Identify risks and mitigation strategies
- Resolve open questions
- Continue using AskUserQuestion for decisions
- Apply YAGNI ruthlessly — remove unnecessary features from the design

### 5. Write the Spec Doc

Capture the agreed design in a spec doc:

- **Location**: Check CLAUDE.md for a dev docs directory convention
  (e.g., `dev/`, `docs/dev/`). Save to that directory, creating it if
  needed. If no convention is found, save to the project root.
- **Filename**: `spec-<kebab-case-name>.md`

**Spec doc contents:**
- Summary (motivation + outcome)
- Requirements (what the feature must do)
- Design decisions (with alternatives considered and rationale)
- Scope (in scope / out of scope)
- Architecture overview (components, data flow, key interfaces)
- Constraints (performance, compatibility, dependencies)
- Open questions (anything unresolved)

### 6. Hand Off to Plan

Ask the user via AskUserQuestion whether to proceed:

> "Spec written to `<path>`. Ready to create the implementation plan?"

Options:
- "Yes, proceed to /plan" — Create phased implementation plan from
  this spec
- "Review spec first" — I want to review/edit the spec before planning
- "Done for now" — I'll plan later

If the user selects "Yes", immediately invoke the **plan** skill (via
the Skill tool) with the spec doc path as context, noting that design
decisions are already resolved in the spec.

## Hard Gate

Do NOT write code during brainstorming. This skill produces a spec doc,
not implementation. If the user asks to start coding, suggest completing
the brainstorm first, then using `/plan` followed by `/implement`.

## Common Mistakes

- Asking multiple questions in one message (one at a time)
- Using plain text questions instead of AskUserQuestion
- Jumping to implementation before the design is agreed
- Over-designing: adding features nobody asked for (YAGNI)
- Not exploring alternatives: settling on the first approach
- Skipping the spec doc and going straight to planning

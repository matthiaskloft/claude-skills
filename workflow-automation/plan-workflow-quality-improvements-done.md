# Plan: Workflow Quality Improvements

**Created**: 2026-03-21
**Author**: Claude

## Status

| Phase | Status | Date | Notes |
|-------|--------|------|-------|
| Plan | DONE | 2026-03-21 | Approved with modifications |
| Phase 1: Implementer status protocol | IMPLEMENTED | 2026-03-21 | |
| Phase 2: Stop-and-escalate protocol | IMPLEMENTED | 2026-03-21 | |
| Phase 3: Verification gate in ship | IMPLEMENTED | 2026-03-21 | |
| Phase 4: Official Anthropic subagent types + AskUserQuestion | IMPLEMENTED | 2026-03-21 | |
| Phase 5: TDD enforcement | SKIPPED | 2026-03-21 | User decision: current test guidance sufficient |
| Phase 6: Anthropic agent catalog + soft model guidance | IMPLEMENTED | 2026-03-21 | |
| Phase 7: Brainstorm skill (spec doc output) | IMPLEMENTED | 2026-03-21 | |
| Ship | TODO | | |

## Summary

**Motivation**: Analysis of the official Superpowers plugin (v5.0.2)
revealed that our workflow-automation plugin has strong end-to-end
automation (plan-to-merge pipeline, cron-based PR monitoring, autonomous
batch mode) but weak per-task quality enforcement. The implement skill's
"deep review loop" uses a single generic `subagent_type=Explore` agent
to check six concerns at once, there is no structured escalation when
phases hit blockers, no verification gate before shipping, no TDD
enforcement, and no pre-plan design exploration phase. Additionally, the
skills reference generic agent dispatches instead of the official
Anthropic subagent types that are purpose-built for each concern.

**Outcome**: After implementation, the workflow-automation plugin will:
- Use official Anthropic subagent types (`feature-dev:code-architect`,
  `feature-dev:code-reviewer`, `pr-review-toolkit:code-reviewer`,
  `pr-review-toolkit:silent-failure-hunter`, `pr-review-toolkit:pr-test-analyzer`,
  `code-simplifier:code-simplifier`) instead of generic agents
- Enforce two-stage review (spec compliance then code quality) with
  parallel dispatch in stage 2
- Define four implementation statuses (IMPLEMENTED, IMPLEMENTED_WITH_CONCERNS,
  NEEDS_INPUT, BLOCKED) with explicit handling for each
- Stop and escalate after 3+ failed fix attempts instead of thrashing
- Run fresh verification before standalone ship invocations (skipped in
  implement-ship flows where tests just ran)
- Use AskUserQuestion as the default interaction tool in brainstorm, and
  for blockers in plan
- Provide a catalog of available Anthropic agents/skills with soft model
  selection guidance
- Offer a brainstorm skill that produces a spec doc for design exploration
  before the plan skill writes the operational plan

## Assumptions

- All official Anthropic subagent types listed in the Agent tool
  description are available in every Claude Code session (they are
  built-in, not plugin-dependent)
- The `monitor-pr` cron prompt should NOT use subagents — cron context
  needs low-latency inline operations, not agent dispatch overhead
- Phase ordering reflects dependency chain and priority (high-impact,
  low-effort phases first)

## Design Decisions

| Decision | Options | Chosen | Rationale |
|----------|---------|--------|-----------|
| Review architecture | (A) Single-pass multi-concern review, (B) Two-stage sequential review (spec then quality), (C) Parallel multi-agent review | B: Two-stage with parallel agents in stage 2 | Spec compliance must pass before quality review is meaningful; within quality, the three agents are independent and can run concurrently |
| Status protocol location | (A) In implement skill only, (B) In shared-references as a protocol, (C) Inline in each skill | A: In implement skill only | Only implement produces phase results; ship and monitor-pr consume statuses but don't define them |
| Brainstorm skill scope | (A) Full Socratic dialogue with visual companion (superpowers-style), (B) Lightweight design exploration producing spec doc, (C) Just add a design decisions step to the plan skill | B: Lightweight brainstorm with spec doc output | Brainstorm produces the design spec; plan produces the operational implementation plan. Clear separation of concerns. |
| Brainstorm vs plan disambiguation | (A) Brainstorm and plan are the same skill, (B) Brainstorm produces spec doc, plan produces operational plan, (C) Brainstorm is just plan Step 1 | B: Separate skills, separate outputs | Brainstorm = "what and why" (spec doc); plan = "how and when" (phased implementation). Brainstorm asks user whether to proceed to /plan at the end. |
| TDD enforcement | (A) Add TDD step structure to plan template and implement, (B) Keep current guidance | B: Keep current guidance | User decision: current "write tests" guidance is sufficient; TDD enforcement risks being too prescriptive for diverse codebases |
| Model selection | (A) Hard-coded model per agent type, (B) Soft guidance + agent catalog, (C) No model guidance | B: Soft guidance + agent catalog | Catalog of available Anthropic agents/skills provides awareness; soft guidance ("consider sonnet for mechanical tasks") avoids stale hardcoded recommendations |
| Ship verification in implement-ship flows | (A) Always run fresh verification, (B) Skip in implement-ship flows | B: Skip in implement-ship flows | When ship runs immediately after implement in the same session, tests just passed moments ago; re-running is redundant overhead |
| Interactive tool for user decisions | (A) Plain text questions, (B) AskUserQuestion tool | B: AskUserQuestion | Structured options with descriptions are clearer than open-ended text questions; default in brainstorm, on-blocker-only in plan |

## Scope

### In Scope

- New `brainstorm` skill (SKILL.md) — produces spec doc, uses AskUserQuestion
- Modified `implement/SKILL.md` (status protocol, stop-and-escalate, official subagent types, soft model guidance, Anthropic agent catalog)
- Modified `ship/SKILL.md` (verification gate, skip in implement-ship flows)
- Modified `plan/SKILL.md` (official subagent type for plan review, AskUserQuestion for blockers, brainstorm suggestion)
- Modified `implement-ship-all/SKILL.md` (reference updated agent types in quality gate)
- Modified `implement-ship/SKILL.md` (gate check for IMPLEMENTED_WITH_CONCERNS, write `mode: "implement-ship"` to state file before delegating)

### Out of Scope

- Changes to `monitor-pr/SKILL.md` — cron prompt stays as-is (inline operations, no subagents)
- Changes to `shared-references/workflow-state.md` — state schema unchanged (IMPLEMENTED_WITH_CONCERNS maps to existing IMPLEMENTED status in the plan table; the distinction is runtime behavior, not persisted state)
- Changes to `shared-references/permissions-template.json` — no new permissions needed
- Changes to `plan/references/plan-template.md` and `plan/references/plan-example.md` — TDD enforcement skipped per user decision
- Parallel phase dispatch (Improvement #8 from analysis) — niche use case, deferred
- Superpowers-style prompt templates for subagents (implementer-prompt.md, spec-reviewer-prompt.md) — official Anthropic agents have their own built-in prompts; we pass focus instructions, not full prompt templates
- Visual brainstorming companion — unnecessary complexity

## Implementation Plan

### Phase 1: Implementer Status Protocol

Add a structured status protocol to `implement/SKILL.md` so phase
execution results are categorized and handled explicitly, especially
in autonomous mode.

**Files to create:**
- None

**Files to modify:**
- `skills/implement/SKILL.md` — add status definitions after Step 7, update Steps 3 and 7 to reference them
- `skills/implement-ship/SKILL.md` — update Gate Check to handle IMPLEMENTED_WITH_CONCERNS

**Steps:**
1. Read `skills/implement/SKILL.md`
2. Add a new section "## Phase Execution Statuses" after the Step-by-Step section, defining four statuses:
   - `IMPLEMENTED` — phase complete, all tests pass, ready to ship
   - `IMPLEMENTED_WITH_CONCERNS` — complete but flagged doubts (e.g., approach may not scale, test coverage uncertain). Concerns are surfaced to the user before shipping (or logged in the plan's Notes in autonomous mode).
   - `NEEDS_INPUT` — blocked on a user decision. In autonomous mode: log the question in the plan's Notes, mark the phase `BLOCKED`, and move to the next phase if independent; otherwise stop.
   - `BLOCKED` — cannot proceed due to technical issue. Triggers the stop-and-escalate protocol (Phase 2).
3. Update Step 3 (Execute the Phase) — append after the existing "Stay on scope" paragraph: "After execution, determine the phase status (see Phase Execution Statuses). If status is not IMPLEMENTED, handle according to the protocol before proceeding."
4. Update Step 7 (Update the Plan) to record the status and any concerns in the plan's Notes section
5. Supersede the "Blocked by a dependency" bullet in the Troubleshooting section — rewrite it to point to the new Phase Execution Statuses section instead of giving standalone BLOCKED handling instructions. This prevents contradictory BLOCKED guidance in two places.
6. Read `skills/implement-ship/SKILL.md`. Make two changes:
   a. **Write mode to state file**: At Step 1 start, before delegating to implement, write `.workflow-state.json` with `mode: "implement-ship"` and `skill: "implement-ship"`. This makes the mode detectable by ship's skip condition (Phase 3). Currently implement-ship claims the mode field is set but has no instruction to actually write it.
   b. **Gate Check for IMPLEMENTED_WITH_CONCERNS**: Update Gate Check (Step 2) to handle `IMPLEMENTED_WITH_CONCERNS`: if the phase completed with concerns, surface them to the user before proceeding to ship. In autonomous mode (detected via `mode: "implement-ship-all"` in the state file), log the concerns in the plan's Notes and proceed rather than pausing. The current Gate Check only mentions `BLOCKED` and `incomplete` — add `IMPLEMENTED_WITH_CONCERNS` as an additional case.
7. Run tests / verify skill files are valid markdown with correct frontmatter

**Depends on:** None

### Phase 2: Stop-and-Escalate Protocol

Add explicit guidance to `implement/SKILL.md` for when to stop fixing
and escalate, preventing the failure mode where autonomous runs thrash
on a problem that needs human judgment.

**Files to create:**
- None

**Files to modify:**
- `skills/implement/SKILL.md` — add stop-and-escalate section, update Troubleshooting

**Steps:**
1. Read `skills/implement/SKILL.md`
2. Add a new section "## When to Stop and Escalate" after the Phase Execution Statuses section (from Phase 1), containing:
   - Stop immediately when: hit a blocker (missing dependency, test fails unexpectedly, instruction unclear)
   - After 3+ fix attempts on the same issue: stop, do not attempt fix #4. The pattern of repeated failures indicates the approach is wrong, not that the fix is almost right.
   - When you don't understand why something fails: ask, don't guess
   - In autonomous mode: mark the phase `BLOCKED`, log what was tried and what failed in the plan's Notes, and stop the loop
3. Update the existing "Troubleshooting" section's "Tests fail unexpectedly" bullet to reference the new escalation protocol
4. Verify the skill file reads coherently end-to-end

**Depends on:** Phase 1 (references BLOCKED status)

### Phase 3: Verification Gate in Ship

Add an explicit evidence-based verification step to `ship/SKILL.md`
that requires fresh test/build output in the current context before
proceeding, not cached results from the implement phase.

**Files to create:**
- None

**Files to modify:**
- `skills/ship/SKILL.md` — strengthen Step 1 (Verify Readiness)

**Steps:**
1. Read `skills/ship/SKILL.md`
2. Strengthen Step 1 (Verify Readiness) with a fresh verification gate:
   - **Read state file**: At the start of Step 1, read `.workflow-state.json` if it exists and extract the `mode` field.
   - **Skip condition**: If `mode` is `"implement-ship"` or `"implement-ship-all"`, skip the fresh test/build verification — implement just ran tests moments ago in the same session. Still check plan status.
   - **Standalone ship**: Run the project's test command and read the full output (exit code, pass/fail counts). Do not rely on "tests passed during implementation" — that was a different context. Run the build command if applicable and verify exit 0.
   - Check phase status in the plan is `IMPLEMENTED` (not `IN_PROGRESS`)
   - Add: "If you cannot produce fresh test output showing 0 failures (standalone ship only), do not proceed to Step 2. Fix the issues first."
   - Preserve the existing user-override path for status: if the phase is `IMPLEMENTED_WITH_CONCERNS`, surface the concerns to the user and ask whether to proceed. In autonomous mode, log the concerns in the plan's Notes and proceed (the implement skill already surfaced them).
   - The test gate (when applicable) is a hard requirement. The status-override path is preserved for non-test issues only.
3. Verify the skill file reads coherently

**Depends on:** None (independent of Phases 1-2)

### Phase 4: Official Anthropic Subagent Types

Replace all generic `subagent_type=Explore` dispatches and vague "if
available" fallback chains with explicit references to official Anthropic
subagent types. This is the largest phase — it touches three skill files.

**Files to create:**
- None

**Files to modify:**
- `skills/plan/SKILL.md` — Step 3: replace `subagent_type=Explore` with `feature-dev:code-architect`; add AskUserQuestion for blocker resolution during review loop
- `skills/implement/SKILL.md` — Step 4: replace generic simplify agent with `code-simplifier:code-simplifier`; Step 5: replace single-pass Explore review with two-stage pipeline using `feature-dev:code-reviewer` + parallel `pr-review-toolkit:code-reviewer`, `pr-review-toolkit:silent-failure-hunter`, `pr-review-toolkit:pr-test-analyzer`
- `skills/implement-ship-all/SKILL.md` — quality gate in batched flow item 5 (~line 133) and split flow item 4 (~line 151): update to reference specific agent types from implement Steps 4-5

**Steps:**
1. Read all three skill files
2. **plan/SKILL.md Step 3**: Replace `subagent_type=Explore` with `subagent_type="feature-dev:code-architect"`. Update both the Agent tool call syntax and the surrounding prose ("Spawn a review agent...") to name the specific agent type and its purpose. Retain the existing review prompt text (lines 74–80) as a focus instruction passed to the agent — official agents accept additional focus prompts on top of their built-in behavior. Update the prompt to focus on plan-vs-codebase validation: feasibility, gaps, risks, scope, cross-checking referenced files/APIs/patterns against actual codebase. Add a model selection note: default model (architectural reasoning requires deep context). Also add: when the review loop surfaces blockers that require a user decision (e.g., ambiguous scope, conflicting constraints), use AskUserQuestion to present the options with descriptions rather than plain text questions.
3. **implement/SKILL.md Step 4 (Simplify)**: Replace the "if available... otherwise" fallback chain with a primary dispatch to `subagent_type="code-simplifier:code-simplifier"` targeting the files modified in this phase. Add a fallback note: "If this agent type is unavailable, fall back to a general-purpose agent with instructions to simplify the changed code for clarity and maintainability."
4. **implement/SKILL.md Step 5 (Deep Review Loop)**: Restructure into two stages:
   - **Stage 1 — Spec compliance** (mandatory first): Spawn `subagent_type="feature-dev:code-reviewer"` with the plan document and changed files. Focus prompt on: all planned steps addressed, no over-building, pattern consistency. Fix blockers/warnings before Stage 2. Cap at 2 iterations for Stage 1 alone — if spec compliance still has blockers after 2 rounds, stop and inform the user.
   - **Stage 2 — Code quality** (only after Stage 1 passes): Spawn three agents in parallel:
     - `pr-review-toolkit:code-reviewer` — project guidelines and CLAUDE.md conventions
     - `pr-review-toolkit:silent-failure-hunter` — error handling, swallowed exceptions
     - `pr-review-toolkit:pr-test-analyzer` — test coverage quality and gaps
   - Collect findings from all three, fix blockers/warnings, re-run Stage 2 until clean.
   - Cap Stage 2 at 3 iterations. If the 3rd iteration still has blockers, stop and inform the user.
   - Fallback: if any agent type is unavailable, fall back to a general-purpose agent with the same focus prompt.
5. **implement-ship-all/SKILL.md**: Update the quality gate in both locations — batched flow item 5 (~line 133) and split flow item 4 (~line 151) — to name the specific agent types: "Run implement Step 4 (Simplify via `code-simplifier:code-simplifier`) and Step 5 (Review via `feature-dev:code-reviewer`, `pr-review-toolkit:code-reviewer`, `pr-review-toolkit:silent-failure-hunter`, `pr-review-toolkit:pr-test-analyzer`)"
6. Verify all three files read coherently and have no dangling references to generic agents

**Depends on:** None (can be done independently, but placed here because it builds on the structural changes from Phases 1-2). Steps within this phase must be executed in order (Step 5 references agent types named in Steps 2–4).

### ~~Phase 5: TDD Enforcement~~ — SKIPPED

_User decision: current test guidance is sufficient. TDD enforcement
risks being too prescriptive for diverse codebases._

### Phase 6: Anthropic Agent Catalog + Soft Model Guidance

Add a reference catalog of available official Anthropic agents and skills
to `implement/SKILL.md`, with soft model selection guidance. Instead of
hardcoded per-agent model recommendations, provide general guidance on
when to consider lighter models.

**Files to create:**
- None

**Files to modify:**
- `skills/implement/SKILL.md` — add Anthropic agent catalog and soft model guidance section

**Steps:**
1. Read `skills/implement/SKILL.md`
2. Add a "## Available Anthropic Agents" section after the review loop. Frame it as: "This catalog covers agents available to the workflow automation skills. The plan skill uses `feature-dev:code-architect` for plan review — see plan/SKILL.md Step 3 for that agent's role." Then catalog the official subagent types and their purposes:
   - **Review agents**: `feature-dev:code-reviewer` (bugs, logic, security, confidence-filtered), `pr-review-toolkit:code-reviewer` (project guidelines, CLAUDE.md), `pr-review-toolkit:silent-failure-hunter` (error handling, swallowed exceptions), `pr-review-toolkit:pr-test-analyzer` (test coverage gaps), `pr-review-toolkit:comment-analyzer` (comment accuracy), `pr-review-toolkit:type-design-analyzer` (type design)
   - **Implementation agents**: `code-simplifier:code-simplifier` (simplify for clarity/maintainability), `feature-dev:code-architect` (design architectures from existing patterns), `feature-dev:code-explorer` (trace execution paths, map architecture)
   - **Exploration agents**: `Explore` (fast codebase search — general purpose only; do NOT use for code review or simplification, use the dedicated agents above), `Plan` (implementation strategy design)
3. Add a "## Model Selection Guidance" subsection with soft guidance:
   - "Consider using `model: "sonnet"` for mechanical, focused tasks (simplification, pattern-matching against guidelines, scanning for specific error patterns). Use the default model for tasks requiring deep reasoning (spec compliance review, architectural analysis, complex multi-file changes)."
   - "These are suggestions, not rules. The user can override via CLAUDE.md preferences."
4. Verify the section reads coherently in context

**Depends on:** Phase 4 (references the specific agent types introduced there)

### Phase 7: Brainstorm Skill (Spec Doc Output)

Create a new `brainstorm` skill for structured design exploration before
planning. Produces a **spec doc** (the "what and why") that the plan
skill then uses to write the **operational plan** (the "how and when").
Clear separation: brainstorm explores the problem space and documents
the design; plan turns that design into phased implementation steps.

**Files to create:**
- `skills/brainstorm/SKILL.md` — the brainstorm skill definition

**Files to modify:**
- `skills/plan/SKILL.md` — add a note in Step 1 suggesting brainstorm for ambiguous/large requests; update Step 1 to check for existing spec docs from brainstorm

**Steps:**
1. Create `skills/brainstorm/SKILL.md` with:
   - Frontmatter: name, description (trigger phrases: "brainstorm", "explore this idea", "let's discuss the approach", "what are my options for"). Avoid "think through" as a standalone trigger — it collides with plan's "think through how to build" trigger.
   - **Disambiguation note at the top**: "This skill produces a **spec doc** — the design, requirements, and decisions for a feature. It does NOT produce an implementation plan. After brainstorming, use the **plan** skill (`/plan`) to turn the spec into a phased operational plan."
   - Step 1: Explore project context (read CLAUDE.md, relevant code, recent commits)
   - Step 2: Ask clarifying questions using **AskUserQuestion** as the default interaction tool — one question at a time, prefer multiple choice with descriptions. Focus on: purpose, constraints, success criteria, who will use this.
   - Step 3: Propose 2-3 approaches using AskUserQuestion with descriptions and a recommended option marked "(Recommended)". Lead with the recommended approach and explain why.
   - Step 4: Iterate on the chosen approach. Refine scope, identify risks, resolve open questions. Continue using AskUserQuestion for decisions.
   - Step 5: Write a **spec doc** capturing the agreed design. Save to the project's dev docs directory (check CLAUDE.md for convention, fallback to project root). Filename: `spec-<kebab-case-name>.md`. Contents: summary, requirements, design decisions (with alternatives considered), scope (in/out), architecture overview, key interfaces, constraints, open questions.
   - Step 6: Ask user via AskUserQuestion whether to proceed to the plan skill: "Spec written to `<path>`. Ready to create the implementation plan?" Options: "Yes, proceed to /plan" (description: "Create phased implementation plan from this spec"), "Review spec first" (description: "I want to review/edit the spec before planning"), "Done for now" (description: "I'll plan later"). If the user selects "Yes", immediately invoke the **plan** skill (via the Skill tool) with the spec doc path as context, noting that design decisions are already resolved in the spec.
   - Key principles: one question per message, YAGNI ruthlessly, explore alternatives before settling, be willing to go back, AskUserQuestion is the default (not plain text questions)
   - Hard gate: do NOT write code during brainstorming — this skill produces a spec doc, not implementation
2. Read `skills/plan/SKILL.md`
3. Add a note at the end of Step 1 (Understand the Request): "For ambiguous or large-scope requests where the design approach is unclear, suggest using the **brainstorm** skill first to explore the problem space and produce a spec doc before committing to a plan."
4. Update Step 1 to also check for existing spec docs: "Look for `spec-*.md` files in the dev docs directory and the project root (brainstorm falls back to root if no CLAUDE.md convention is found). If a spec exists for the requested feature, use it as the primary source for the plan's Summary, Design Decisions, and Scope sections. Do not re-derive design decisions that the spec already resolved — treat those as settled. Only ask clarifying questions about implementation phasing, not about design choices already documented in the spec."
5. Verify both files

**Depends on:** None (but placed last because it's the highest-effort phase and the other phases deliver more immediate value)

## Verification & Validation

- **Automated**: Each modified skill file must be valid markdown with correct YAML frontmatter (name + description fields). Verify with a markdown linter or manual inspection.
- **Manual**:
  - Read each modified skill end-to-end to confirm it reads coherently — no dangling references, no contradictory instructions, no leftover generic agent mentions
  - Verify that no skill references `subagent_type=Explore` or `subagent_type="Explore"` for review/simplify tasks (grep across all skill files)
  - Verify the brainstorm skill's trigger phrases don't conflict with existing skill triggers (especially plan's "think through how to build")
  - Confirm no `.workflow-state.json` with `skill: "implement"` or `mode: "implement-ship-all"` is active in the target project before deploying Phase 4 changes (in-flight runs could hit unexpected review structure changes)
  - Verify `implement-ship/SKILL.md` Gate Check handles `IMPLEMENTED_WITH_CONCERNS` correctly after Phase 1 changes
  - Dry-run: mentally walk through an `/implement-ship-all` invocation with the updated skills to confirm the flow makes sense

## Dependencies

- No new external dependencies
- All referenced subagent types (`feature-dev:code-architect`, `feature-dev:code-reviewer`, `pr-review-toolkit:code-reviewer`, `pr-review-toolkit:silent-failure-hunter`, `pr-review-toolkit:pr-test-analyzer`, `code-simplifier:code-simplifier`) are built-in to Claude Code — no plugin installation required

## Notes

_Living section — updated during implementation._

- The analysis that motivated these improvements compared Superpowers v5.0.2 (official Anthropic plugin) against workflow-automation v0.5.0
- Improvement #8 from the analysis (parallel phase dispatch) was deliberately excluded — it's a niche optimization with high implementation complexity and risk of merge conflicts between parallel worktrees
- monitor-pr is explicitly out of scope because its cron prompt needs low-latency inline operations, and subagent dispatch would add overhead to a polling loop

## Review Feedback

Reviewed in 2 iterations.

**Iteration 1**: 13 findings (2 blockers, 8 warnings, 3 suggestions). All addressed:
- Blockers: defined independent iteration caps for two-stage review (Stage 1: 2, Stage 2: 3); replaced non-existent "Step 2.5" with actual file locations
- Warnings: updated prose alongside syntax replacements; preserved user-override path in ship; added agent type fallbacks; added plan-example.md to scope; superseded contradictory Troubleshooting bullet; moved orphaned model guidance; added in-flight state check; fixed trigger phrase collision; added implement-ship autonomous mode clause
- Suggestions: explicit TDD step ordering for both example phases; fixed Phase 5 dependency on Phase 1; added implement-ship Gate Check handling

**Iteration 2**: 5 findings (0 blockers, 3 warnings, 2 suggestions). All addressed:
- Warnings: added autonomous mode clause to implement-ship Gate Check; clarified review prompt retention as focus instruction; added TDD template as minimal guide not prescriptive replacement
- Suggestions: wrote explicit target step orderings for plan-example.md phases; added intra-phase ordering note to Phase 4
- (Note: Phase 5 TDD enforcement was subsequently skipped per user decision — the TDD-related changes described above were not implemented.)

**Iteration 3**: 8 findings (1 blocker, 4 warnings, 3 suggestions). All addressed:
- Blocker: implement-ship must write `mode: "implement-ship"` to state file before delegating, otherwise ship's skip condition is undetectable
- Warnings: ship/SKILL.md needs explicit state file read at Step 1; spec doc consumption too vague ("use as input" → explicit section mapping); Explore in catalog needs "not for review" clarification; catalog needs framing and plan skill cross-reference
- Suggestions: spec doc location search must include project root fallback; brainstorm Step 6 "proceed to /plan" needs mechanical Skill tool invocation; stale TDD references in review feedback annotated

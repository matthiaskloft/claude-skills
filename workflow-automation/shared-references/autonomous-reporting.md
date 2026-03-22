# Autonomous Reporting Formats

Reporting formats used during autonomous runs (auto-implement).

## Progress Dashboard

Print this dashboard at each phase transition (start of loop, after
each phase merges, and at completion). Replace the phase names and
statuses with actual values.

```
╔══ Autopilot: {feature name} ═══════════════╗
║ Phase 1: Core export        ✓ MERGED       ║
║ Phase 2: CLI integration    ⟳ PR_OPEN       ║
║ Phase 3: Documentation      ▸ IN_PROGRESS   ║
║ Phase 4: Release notes       · TODO          ║
╚═════════════════════════════════════════════╝
```

Status indicators:
- `✓` — MERGED (done)
- `⟳` — PR_OPEN (PR created, CI/review in progress)
- `▸` — IN_PROGRESS (currently implementing this phase)
- `·` — TODO (not started)
- `✗` — BLOCKED or FAILED (stopped)

## Workflow Friction Log

Throughout the autonomous run, track any issues, friction points, or
unexpected situations encountered. At completion (or when stopped by
a blocker), print a structured report:

```
╔══ Workflow Friction Log ═══════════════════════╗
║ {N} issues tracked during autonomous run       ║
╚════════════════════════════════════════════════╝
```

Followed by a table:

| # | Phase | Category | Description | Impact | Suggestion |
|---|-------|----------|-------------|--------|------------|

**Categories to track:**
- **prompt-gap** — A skill's instructions were ambiguous or missing,
  requiring a judgment call that could have been codified
- **tool-friction** — A tool call failed, required retries, or behaved
  unexpectedly (e.g., CronCreate quirks, `gh` CLI edge cases)
- **plan-deviation** — The plan's steps didn't match reality (files
  moved, APIs changed, missing dependencies)
- **review-churn** — The deep review loop required 4+ iterations,
  suggesting the plan or implementation guidance was underspecified
- **ci-friction** — CI failures that were hard to diagnose or required
  workarounds
- **state-issue** — State tracking or resume didn't work as expected
- **scope-creep** — Had to make changes outside the phase's listed files

**Impact levels:**
- **blocker** — Stopped the autonomous run
- **slowdown** — Added significant time but didn't stop
- **minor** — Small friction, easily worked around

This log serves two purposes:
1. **Immediate**: Helps the user understand what happened during the
   autonomous run and what to watch for in future runs
2. **Meta-improvement**: Identifies patterns that should be fixed in
   the workflow skills themselves — if a category keeps appearing, the
   corresponding skill needs better instructions

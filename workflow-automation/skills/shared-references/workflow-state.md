# Workflow State File

All workflow skills (implement, ship, monitor-pr, implement-ship,
implement-ship-all) use a shared `.workflow-state.json` file for
cross-session resume. This file is written at key step transitions
and read on startup to detect resumable work.

## Location

The state file lives in the same directory as the plan document:
- If the plan is at `dev/plans/plan-csv-export.md`, the state file
  is at `dev/plans/.workflow-state.json`
- If no plan exists (ad-hoc implementation), place it in the project
  root

## Schema

```json
{
  "plan": "dev/plans/plan-csv-export.md",
  "phase": "Phase 2: CLI integration",
  "skill": "implement",
  "step": 3,
  "step_name": "Execute the Phase",
  "branch": "feat/csv-export-phase2",
  "worktree": "../feat-csv-export-phase2",
  "base_branch": "feat/csv-export-phase1",
  "pr_number": null,
  "monitor_cron_id": null,
  "mode": "implement-ship-all",
  "in_flight_pr": {
    "phase": "Phase 1: Core export",
    "branch": "feat/csv-export-phase1",
    "pr_number": 42,
    "monitor_cron_id": "abc123"
  },
  "last_updated": "2026-03-10T14:32:00Z"
}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `plan` | string | Relative path to the plan document |
| `phase` | string | Name of the active phase |
| `skill` | string | Currently running skill: `implement`, `ship`, `monitor-pr` |
| `step` | number | Current step number within the skill |
| `step_name` | string | Human-readable step name |
| `branch` | string | Git branch for this phase |
| `worktree` | string \| null | Worktree path, or null if using a regular branch |
| `base_branch` | string \| null | Branch this phase was created from. Defaults to main. In pipeline mode, may be a predecessor's feature branch |
| `pr_number` | number \| null | PR number if created, otherwise null |
| `monitor_cron_id` | string \| null | CronCreate job ID if monitoring is active |
| `mode` | string | `single` (one phase), `implement-ship`, or `implement-ship-all` |
| `in_flight_pr` | object \| null | Predecessor phase's PR being monitored in background (pipeline mode only). Contains `phase`, `branch`, `pr_number`, `monitor_cron_id` |
| `last_updated` | string | ISO 8601 timestamp |

## Read Protocol (all skills)

On startup, before doing anything else:
1. Look for `.workflow-state.json` in the plan's directory (or project root)
2. If found, read it and check if the state is relevant:
   - Does the `plan` field match the current plan?
   - Is the `phase` still incomplete (not `MERGED` in the plan)?
   - Is the `branch` or `worktree` still present?
3. If the state is stale (phase already merged, branch deleted), delete
   the state file and start fresh.
4. If the state is valid, offer to resume: "Found in-progress work:
   {skill} step {step} ({step_name}) for {phase}. Resume or start over?"
5. In **autonomous mode** (invoked by implement-ship-all): resume
   automatically without asking.

## Write Protocol (per skill)

### implement
- **Step 2** (phase selected): Write initial state with skill=implement, step=2
- **Step 3** (executing): Update step=3
- **Step 5** (deep review): Update step=5
- **Step 7** (update plan): Update step=7, then clear state after completion
- **Step 8** (next steps): Advisory only — no state update

### ship
- **Step 2** (commit): Write/update with skill=ship, step=2
- **Step 3** (PR created): Update step=3, set pr_number
- **Step 4** (monitoring): Update step=4 (monitor-pr takes over state)

### monitor-pr
- **Step 4** (cron created): Update skill=monitor-pr, set monitor_cron_id
- **Post-merge cleanup**: Clear the state file after successful merge

### implement-ship
- Delegates to implement and ship, which handle their own state.
  The `mode` field is set to `"implement-ship"`.

### implement-ship-all
- Delegates to implement and ship, which handle their own state.
  The `mode` field is set to `"implement-ship-all"`.
- **Pipeline tracking**: When a phase's PR is created and monitoring
  starts, the phase's PR info is moved to `in_flight_pr` before the
  next phase begins. On resume, check `in_flight_pr` to determine if
  a predecessor PR needs monitoring or has merged.
- `base_branch` is set to the predecessor's feature branch when
  pipelining, so the implement skill branches from it.

## Lifecycle

1. Created when a skill starts working on a phase
2. Updated at each major step transition
3. Cleared (deleted) when the phase is successfully merged or abandoned

## Notes

- The state file is local workflow state, not project content. Add
  `.workflow-state.json` to your `.gitignore` to avoid committing it.
- If the state file conflicts with the plan's status table, the plan
  is the source of truth. Delete the state file and reconcile.
- The state file tracks ONE active phase plus optionally one in-flight
  predecessor PR (via `in_flight_pr`). When a phase completes and the
  next one starts, the current phase's PR info moves to `in_flight_pr`
  and the new phase takes the main fields.
- `base_branch` records what branch a phase was created from. In
  pipeline mode this is the predecessor's feature branch; otherwise
  it's the main branch. This is needed for reconciliation rebases.

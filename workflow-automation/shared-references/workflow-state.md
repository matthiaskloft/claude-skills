# Workflow State File

All workflow skills (implement, ship, monitor-pr, auto-implement) use
a shared `.workflow-state.json` file for
cross-session resume. This file is written at key step transitions
and read on startup to detect resumable work.

## Location

The state file lives in the project root (`.workflow-state.json`).
Add it to `.gitignore` to avoid committing it.

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
  "pr_number": null,
  "monitor_cron_id": null,
  "mode": "auto-implement",
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
| `pr_number` | number \| null | PR number if created, otherwise null |
| `monitor_cron_id` | string \| null | CronCreate job ID if monitoring is active |
| `mode` | string \| null | `"auto-implement"` (autonomous) or `null`/absent (standalone, one phase at a time) |
| `last_updated` | string | ISO 8601 timestamp |

## Read Protocol (all skills)

On startup, before doing anything else:
1. Look for `.workflow-state.json` in the project root
2. If found, read it and check if the state is relevant:
   - Does the `plan` field match the current plan?
   - Is the `phase` still incomplete (not `MERGED` in the plan)?
   - Is the `branch` or `worktree` still present?
3. If the state is stale (phase already merged, branch deleted), delete
   the state file and start fresh.
4. If the state is valid, offer to resume: "Found in-progress work:
   {skill} step {step} ({step_name}) for {phase}. Resume or start over?"
5. In **autonomous mode** (invoked by auto-implement): resume
   automatically without asking.

## Write Protocol (per skill)

### implement
- **Step 2** (phase selected): Write initial state with skill=implement, step=2
- **Step 3** (executing): Update step=3
- **Step 5** (review loop): Update step=5
- **Step 7** (update plan): Update step=7, then clear state after completion
- **Step 8** (next steps): Advisory only — no state update

### ship
- **Step 2** (commit): Write/update with skill=ship, step=2
- **Step 3** (PR created): Update step=3, set pr_number
- **Step 4** (monitoring): Update step=4 (monitor-pr takes over state)

### monitor-pr
- **Step 4** (cron created): Update skill=monitor-pr, set monitor_cron_id
- **Post-merge cleanup**: Delete the state file after successful merge.

### auto-implement
- Delegates to implement and ship, which handle their own state.
  The `mode` field is set to `"auto-implement"`.

## Lifecycle

1. Created when a skill starts working on a phase
2. Updated at each major step transition
3. Cleared (deleted) when the phase is successfully merged or abandoned

## Notes

- The state file is local workflow state, not project content. Add
  `.workflow-state.json` to your `.gitignore` to avoid committing it.
- If the state file conflicts with the plan's status table, the plan
  is the source of truth. Delete the state file and reconcile.
- The state file tracks ONE active phase at a time. When a phase
  merges, the state file is deleted. The next phase creates a fresh
  state file when it starts.

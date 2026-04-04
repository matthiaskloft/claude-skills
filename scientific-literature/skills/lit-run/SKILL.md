---
name: lit-run
description: Orchestrate pipeline steps and launch worker agents.
---

# lit-run

1. Read `pipeline_state.json`.
2. Resolve next ready step with dependency checks.
3. Execute script steps (`A1`-`A3`, `A6`-`A8`) with minimal context.
4. Launch agents for abstract/full-text review steps and pass only required inputs declared in agent files.
5. Mark step status through `lib/pipeline_state.py`.

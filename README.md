# claude-skills

A monorepo of Claude Code plugins for scientific computing, code review, and workflow automation.

## Plugins

### bayesflow-skills

Domain-specific skills for [BayesFlow 2.x](https://github.com/bayesflow-org/bayesflow) extension packages. Provides patterns and best practices for building BayesFlow extensions.

| Skill | Description |
|-------|-------------|
| **bayesflow-simulator** | Data-generating processes with `@allow_batch_size`, RNG discipline, and prior/likelihood/meta functions |
| **keras-ops** | Backend-agnostic tensor math using `keras.ops.*` for loss functions, layers, and forward passes |
| **bayesflow-adapter** | Data preprocessing pipelines, three-slot schema, and standardization transforms |
| **bayesflow-testing** | Test patterns with `conftest.py` setup, shape testing, and mocking |
| **bayesflow-validation** | Simulation-based calibration (SBC), coverage metrics, and quality gates |
| **bayesflow-memory** | GPU memory management, OOM recovery, and gradient checkpointing |
| **bayesflow-packaging** | Package structure, `__all__` exports, `pyproject.toml`, and CI configuration |

Skills trigger automatically based on task context (e.g., creating a simulator, debugging OOM errors, writing tests). You can also invoke them explicitly via the `bayesflow-skills:` namespace.

---

### code-sentinel

Independent code review via specialized subagents. Reviews uncommitted changes for bugs, security issues, silent errors, and logical inconsistencies. Specialized for **R** and **Python** codebases.

| Skill | Description |
|-------|-------------|
| **code-sentinel** | Orchestrates independent review subagents that audit your diff with no prior context of the implementation |

**Usage:** Ask Claude to "review my changes", "check my code before committing", or "audit this diff". The skill delegates to subagents that have no knowledge of the implementing conversation, ensuring unbiased review.

---

### workflow-automation

A Plan/Implement/Ship workflow for structured feature development. Breaks large features into phases, implements them in worktrees, and ships each phase as a PR with CI monitoring.

| Skill | Description |
|-------|-------------|
| **plan** | Create a structured design document before implementation — scope, decisions, and phased steps |
| **implement** | Build from a plan document phase by phase, with cross-session resume via state tracking |
| **ship** | Commit, create a PR, monitor CI, and merge a completed phase |
| **implement-ship** | Implement a phase and ship it (commit, PR, CI, merge) in one session |
| **implement-ship-all** | Autonomously implement and ship all remaining phases from a plan |
| **monitor-pr** | Background CI monitoring with auto-merge — checks status every 4 minutes and fixes failures |

**Usage (after installation):** Start with `/plan` to design a feature, then `/implement` to build it phase by phase, and `/ship` to get it merged. For a fully autonomous flow, use `/implement-ship-all` (or say "autopilot") to run from plan to merged PRs without stopping.

## Installation

Install plugins using Claude Code's `/install-plugin` command. See the [Claude Code plugins documentation](https://docs.anthropic.com/en/docs/claude-code/plugins) for the latest syntax.

```shell
# Install from GitHub directly
/install-plugin matthiaskloft/claude-skills/bayesflow
/install-plugin matthiaskloft/claude-skills/code-sentinel
/install-plugin matthiaskloft/claude-skills/workflow-automation
```

## How it works

Once installed, skills activate automatically based on what you ask Claude to do. Each plugin adds its skills to Claude Code's context, and the matching skill triggers when your request fits its description.

You can also invoke any skill explicitly using slash commands (e.g., `/plan`, `/ship`) or by referencing the plugin-qualified name (e.g., `bayesflow-skills:bayesflow-simulator`, `workflow-automation:plan`).

## License

[MIT](LICENSE)

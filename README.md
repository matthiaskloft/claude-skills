# claude-skills

Claude Code plugins for scientific computing and Bayesian inference workflows.

## Plugins

### bayesflow-skills

Domain-specific skills for [BayesFlow 2.x](https://github.com/bayesflow-org/bayesflow) extension packages. Provides patterns and best practices for:

| Skill | Description |
|-------|-------------|
| **bayesflow-simulator** | Data-generating processes, `@allow_batch_size`, RNG discipline |
| **keras-ops** | Backend-agnostic tensor math with `keras.ops.*` |
| **bayesflow-testing** | Test patterns, `conftest.py` setup, shape testing, mocking |
| **bayesflow-adapter** | Data preprocessing pipelines, three-slot schema, standardization |
| **bayesflow-validation** | SBC calibration, coverage metrics, condition grids, quality gates |
| **bayesflow-memory** | GPU memory management, OOM recovery, gradient checkpointing |
| **bayesflow-packaging** | Package structure, `__all__`, `pyproject.toml`, CI configuration |

## Installation

### From the marketplace

Add this repository as a Claude Code marketplace, then install the plugin:

```shell
/plugin marketplace add matthiaskloft/claude-skills
/plugin install bayesflow-skills@matthiaskloft-claude-skills
```

### Direct plugin install

You can also install the plugin directly without adding the marketplace:

```shell
/plugin install bayesflow-skills --source github:matthiaskloft/claude-skills/bayesflow
```

## Usage

Once installed, Claude Code automatically invokes the relevant skill based on task context. You can also invoke skills manually — they appear under the `bayesflow-skills` namespace.

## License

[MIT](LICENSE)

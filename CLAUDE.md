# claude-skills

Multi-plugin monorepo for Claude Code plugins targeting scientific computing and Bayesian inference.

## Repository Structure

- `bayesflow/` - BayesFlow 2.x domain skills plugin (simulators, adapters, testing, validation, memory, packaging, keras-ops)
- `code-sentinel/` - Independent code review plugin with subagent orchestration
- `workflow-automation/` - Plan/Implement/Ship workflow automation plugin

## Plugin Convention

Each plugin directory contains:
- `plugin.json` - Plugin manifest (name, description, version)
- `skills/` - Skill definitions (`.md` files or directories with `SKILL.md` + `references/`)

## Development Notes

- Platform: Windows 11 with bash shell
- Skills use markdown format with YAML frontmatter for metadata
- When creating new skills, follow the existing pattern in `bayesflow/skills/`

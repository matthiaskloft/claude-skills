# claude-skills

Multi-plugin monorepo for Claude Code plugins targeting scientific computing, Bayesian inference,
and workflow automation. Content useful across most sessions lives in the separate
`agentic_coding_ressources/global-memory/` repo instead (personal skills, cross-project memory);
this repo holds project/domain-specific plugins that make sense as opt-in installs.

## Repository Structure

- `bayesflow/` - BayesFlow 2.x domain skills plugin (simulators, adapters, testing, validation, memory, packaging, keras-ops)
- `workflow-automation/` - Plan/Implement/Ship workflow automation plugin
- `scientific-literature/` - Domain-agnostic literature management plugin (OpenAlex search, citation, BibTeX export, full-text acquisition, extraction, crawling, pipeline orchestration)

`code-sentinel/` was removed from this repo — it's broadly useful across most sessions, so it
moved to `agentic_coding_ressources/global-memory/skills/code-sentinel/` as a personal skill
instead of staying a per-machine plugin install.

## Plugin Convention

Each plugin directory contains:
- `plugin.json` - Plugin manifest (name, description, version)
- `skills/` - Skill definitions (`.md` files or directories with `SKILL.md` + `references/`)

## Development Notes

- Platform: Windows 11 with bash shell
- Skills use markdown format with YAML frontmatter for metadata
- When creating new skills, follow the existing pattern in `bayesflow/skills/`

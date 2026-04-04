# Plan: `scientific-literature` Plugin

## Context

All 5 BayesFlow repos share the same CLAUDE.md mandate — verify references via OpenAlex, APA 7 format, source-backed implementation. Only `bayesflow_irt_article` has real infrastructure (7 Python scripts, 2 agents, 1 orchestrator skill) and `bayesflow_hpo` has a well-maintained `references.md`. The other 3 repos have zero tooling. Existing code is entirely hardcoded to IRT topics — nothing is reusable across repos.

**Goal:** A new plugin in the `claude-skills` monorepo that generalizes all of this into a reusable, token-efficient, domain-agnostic literature management system.

---

## Design Decisions (finalized)

| Decision | Choice |
|----------|--------|
| Plugin location | New plugin in `claude-skills/scientific-literature/` |
| Python code | **Hybrid**: fixed `lib/` engine modules + templates for config-heavy scripts |
| Script/module resolution | Scripts use `__file__` auto-detection for `lib/`; skills reference via `<plugin-path>/scripts/` |
| Orchestration | `/lit-run` reads config, assembles context, passes it to subagents at invocation. Agent `.md` files declare required inputs explicitly. |
| Skill structure | Separate atomic skills (11 total — see below) |
| Config format | Minimal `litreview.yaml` (paths, project info) + `litreview/` directory with separate YAML files per concern (lazy-loaded per step) |
| Reference store | `_index.json` as source of truth + auto-generated `references.md` |
| Zotero integration | SQLite database query (metadata) + PDF filename scan fallback. Paths user-defined, cached in gitignored file. |
| Migration (irt_article) | Parallel: old scripts stay for completed steps A1-A5; plugin used for A6-A8 onwards |
| Initialization | Merged into `/lit-plan`: interviews user for paths, scaffolds structure, then designs search strategy |
| lit-guide activation | User chooses during `/lit-plan`: pointer line or compact rules in CLAUDE.md |

---

## Plugin Structure

```
claude-skills/
└── scientific-literature/
    ├── plugin.json
    ├── lib/                              # Fixed engine modules (domain-agnostic)
    │   ├── openalex.py
    │   ├── apa7.py
    │   ├── pdf_extract.py
    │   ├── pipeline_state.py
    │   ├── arxiv_client.py
    │   ├── zotero_local.py               # SQLite + PDF scan
    │   └── reference_index.py
    ├── scripts/                          # CLI entry points (thin wrappers)
    │   ├── search.py
    │   ├── validate.py
    │   ├── cite.py
    │   ├── acquire.py
    │   ├── extract.py
    │   ├── crawl.py
    │   ├── title_filter.py               # loads litreview/title_patterns.yaml
    │   ├── abstract_prefilter.py         # loads litreview/abstract_keywords.yaml
    │   └── pipeline_status.py
    ├── templates/                        # For config-heavy generated scripts
    │   ├── title_filter.py.md            # Template with placeholders
    │   └── abstract_scorer.py.md
    ├── shared-references/
    │   ├── source-backed-implementation.md   # Guidance rules + anti-patterns
    │   ├── pipeline-state-schema.md          # pipeline_state.json schema
    │   ├── index-schema.md                   # _index.json schema
    │   └── litreview-yaml-reference.md       # Config file documentation
    ├── agents/                           # Agent prompt files (invoked by /lit-run)
    │   ├── lit-abstract-reviewer.md      # haiku worker: abstract screening
    │   └── lit-triager.md                # sonnet worker: full-text triage
    └── skills/
        ├── lit-guide/SKILL.md
        ├── lit-plan/SKILL.md
        ├── lit-search/SKILL.md
        ├── lit-validate/SKILL.md
        ├── lit-cite/SKILL.md
        ├── lit-acquire/SKILL.md
        ├── lit-extract/SKILL.md
        ├── lit-crawl/SKILL.md
        ├── lit-run/SKILL.md
        └── lit-status/SKILL.md
```

---

## Skills (10 total)

### Core skills (all repos)

| Skill | Purpose | Trigger |
|-------|---------|---------|
| `/lit-guide` | Source-backed implementation rules + anti-patterns. Auto-triggers on cite/reference/paper/DOI context. | Broad auto-trigger on literature-adjacent work |
| `/lit-plan` | Initialize project (interview user for paths, scaffold structure, update CLAUDE.md), then design search strategy (categories, keywords, Mode A/B). Detects existing config and skips completed steps. | Explicit invocation |
| `/lit-search` | OpenAlex keyword search. Display results. Offer to add to `_index.json`. | Explicit or "search for papers on..." |
| `/lit-validate` | Verify a reference (DOI or author+title) against OpenAlex. Report discrepancies. Output APA 7. | Explicit or "verify this reference" |
| `/lit-cite` | Generate APA 7 from DOI/title. Write to `_index.json`. Regenerate `references.md`. | Explicit or "cite this paper" |
| `/lit-acquire` | Find full text: Zotero SQLite → Zotero PDFs → OpenAlex OA → arXiv. Update `_index.json` with pdf path. | Explicit or "get full text for..." |

### Pipeline skills (article/review repos)

| Skill | Purpose |
|-------|---------|
| `/lit-extract` | PDF → structured markdown with section detection. Save to configured references dir. |
| `/lit-crawl` | Forward/backward citation chain crawling from seeds in `litreview/crawl_config.yaml`. |
| `/lit-run` | Pipeline orchestrator. Reads `pipeline_state.json`, identifies next steps, runs scripts or launches agents with full assembled context. |
| `/lit-status` | Read-only view of pipeline step status. No side effects. |

---

## Agents (2)

Both agents are **generic workers** located in `scientific-literature/agents/`. Their `.md` files declare explicitly what project-specific inputs they require. The `/lit-run` skill resolves agent paths relative to the plugin root via `<plugin-path>/agents/<name>.md` and passes them to `claude --agent` at invocation. The `/lit-run` orchestrator assembles required inputs from `litreview/categories.yaml` + other config before invoking each agent.

| Agent | Model | Required inputs from orchestrator |
|-------|-------|-----------------------------------|
| `lit-abstract-reviewer` | haiku | project description, categories table, include criteria, exclude criteria, input/output paths |
| `lit-triager` | sonnet | categories table, tier rules per category, extract sections per category, input/output paths |

---

## Python Library (`lib/`)

All modules are domain-agnostic. Scripts find `lib/` via `__file__` auto-detection.

### `lib/openalex.py`
**Source:** Consolidates duplicate implementations from `a1_keyword_search.py:29-88`, `a8_completeness_crawl.py`, `b_targeted_search.py`

```python
def openalex_search(query, filters=None, per_page=50, max_pages=4, select=DEFAULT_SELECT) -> list[dict]
def openalex_filter_search(title_keywords, author_name, extra_filters="", per_page=5) -> list[dict]
def resolve_doi(doi) -> dict | None
def get_oa_url(openalex_id) -> dict
def get_citations(openalex_id, max_results=200) -> list[dict]
def get_references(openalex_id, max_results=200) -> list[dict]
def reconstruct_abstract(inverted_index) -> str         # consolidates 3 duplicate implementations
def extract_work_info(work) -> dict                     # normalizes OpenAlex work record
```

### `lib/apa7.py`
**Source:** New module — automates currently manual APA 7 formatting

```python
def format_apa7(metadata: dict) -> str         # handles articles, conferences, preprints, books
def format_authors_apa7(authors: list[str]) -> str
def metadata_from_openalex(work: dict) -> dict
```

### `lib/pdf_extract.py`
**Source:** `a7_extract_fulltexts.py` — section patterns are already domain-agnostic

```python
def extract_pdf(pdf_path) -> tuple[str, int]
def detect_sections(text) -> list[dict]
def sections_to_markdown(sections, metadata) -> str
def build_skeleton(sections) -> list[dict]             # ~2-3k tokens/paper (Pass 1)
def build_category_extract(sections, target_sections) -> list[dict]   # Pass 2
```

### `lib/pipeline_state.py`
**Source:** `bayesflow_irt_article/litreview/scripts/pipeline_state.py` — parameterize state file path

```python
class PipelineState:
    def __init__(self, state_file: str)
    def mark_step(step_name, status, notes=None, stats=None)
    def get_next_steps() -> list[str]
    def check_dependencies(step_name) -> tuple[bool, list[str]]
    def print_status()
```

### `lib/zotero_local.py`
**Source:** `a6_acquire_fulltexts.py:57-129` + new SQLite support

```python
class ZoteroSearch:
    """Search Zotero by SQLite metadata first, fall back to PDF filename scan.
    Paths from config (user-defined, cached in gitignored .lit-cache.json).
    Auto-discovers common locations if not configured."""
    def __init__(self, config: dict)
    def search(self, title=None, doi=None) -> tuple[str | None, dict]
    def _search_sqlite(self, title, doi) -> tuple[str | None, dict]    # precise
    def _scan_pdfs(self, title) -> tuple[str | None, float]            # fallback
```

Zotero paths: user-defined during `/lit-plan`, stored in `.lit-cache.json` (gitignored), not in `litreview.yaml` (which is tracked).

### `lib/arxiv_client.py`
**Source:** `a6_acquire_fulltexts.py:171-233`

```python
def arxiv_search(query, max_results=3) -> list[dict]
def download_pdf(url, filepath) -> tuple[bool, int | str]
def download_tex_source(arxiv_id, dest_dir) -> str | None
```

### `lib/reference_index.py`
**Source:** New — generalizes `_index.json` handling

```python
class ReferenceIndex:
    def __init__(self, index_path: str)
    def add(self, citekey, metadata)
    def get(self, citekey) -> dict | None
    def find_by_doi(self, doi) -> tuple[str, dict] | None
    def find_by_title(self, title, threshold=0.8) -> tuple[str, dict] | None
    def generate_citekey(self, authors: list[str], year: int) -> str   # uses authors[0] last name
    def to_references_md(self, output_path)      # auto-generates APA 7 .md
```

---

## Config Structure (per project)

### `litreview.yaml` (minimal, always-read)
```yaml
project:
  name: "bayesflow_hpo"
  description: "..."
  user_agent: "BayesflowHPO/1.0"

paths:                            # user-defined during /lit-plan
  references_dir: "docs/references"
  references_md: "docs/references.md"
  pipeline_data: "litreview/pipeline_data"   # optional, pipeline repos only
  fulltexts_dir: "litreview/fulltexts"       # optional
```

### `litreview/` directory (lazy-loaded per step)
```
litreview/
├── categories.yaml          # read by agents (abstract-reviewer, triager)
├── search_profiles.yaml     # read by /lit-search, /lit-run A1+B
├── title_patterns.yaml      # read by title_filter.py script
├── abstract_keywords.yaml   # read by abstract_prefilter.py script
└── crawl_config.yaml        # read by /lit-crawl
```

### `.lit-cache.json` (gitignored, user-local)
```json
{
  "zotero_sqlite": "/mnt/c/Users/Matze/Nexthessenbox/Zotero/zotero.sqlite",
  "zotero_storage": "/mnt/c/Users/Matze/Nexthessenbox/Zotero/storage",
  "zotero_articles": "/mnt/c/Users/Matze/Nexthessenbox/Zotero_Articles"
}
```

**Path scope:** WSL POSIX paths only (`/mnt/c/...`). Native Windows paths (`C:\...`) are not supported. All file I/O in `zotero_local.py` and `arxiv_client.py` uses Python's `pathlib.Path` with POSIX semantics.

---

## Reference Data Formats

### `_index.json` (source of truth)
```json
{
  "akiba_et_al_2019": {
    "title": "Optuna: ...",
    "authors": ["Akiba, T.", "Sano, S.", "Yanase, T.", "Ohta, T.", "Koyama, M."],
    "authors_str": "Akiba, T., Sano, S., Yanase, T., Ohta, T., & Koyama, M.",
    "year": 2019,
    "journal": "KDD 2019", "doi": "https://doi.org/10.1145/3292500.3330701",
    "openalex_id": "https://openalex.org/W...",
    "categories": ["optuna"],
    "source": ["fulltext"],
    "pdf": "docs/references/akiba_et_al_2019.pdf",
    "apa7": "Akiba, T., Sano, S., Yanase, T., Ohta, T., & Koyama, M. (2019). Optuna ...",
    "added_at": "2026-04-04"
  }
}
```

### `references.md` (auto-generated from `_index.json`)
APA 7 flat list with optional summary paragraphs. Regenerated by `reference_index.to_references_md()`.

---

## Token Efficiency Design

| Principle | Implementation |
|-----------|----------------|
| Config lazy-loaded | `litreview/*.yaml` only read by the specific step that needs it |
| Pipeline steps A1-A3 | Zero tokens (pure Python scripts) |
| Abstract review (A4) | haiku model, ~400 tokens/paper |
| Full-text extraction (A7) | Two-pass: Pass 1 skeleton (~2-3k tokens/paper), Pass 2 targeted sections only |
| Agent context | Orchestrator passes only the config subset each agent needs |
| Skills are small | Each skill focused on one concern; no monolithic prompts |
| `litreview.yaml` | Minimal (paths only); heavy config in separate files |

---

## Migration (bayesflow_irt_article)

Parallel adoption — preserve completed pipeline work:
- Steps A1-A5: existing scripts remain untouched (pipeline data already generated)
- Steps A6-A8: new plugin-based scripts; `/lit-run` orchestrates using `pipeline_state.json`
- `/lit-plan` generates `litreview.yaml` + `litreview/*.yaml` from the hardcoded config in the old scripts
- `_index.json` generated from existing `docs/references/` markdown files

---

## Build Order

1. `plugin.json` + `shared-references/` documents
2. `lib/openalex.py` (core dependency)
3. `lib/apa7.py` + `lib/reference_index.py` (needed by cite/validate)
4. `lib/zotero_local.py` + `lib/arxiv_client.py` (acquisition)
5. `lib/pdf_extract.py` (extraction)
6. `lib/pipeline_state.py` (orchestration)
7. `scripts/` CLI wrappers
8. `templates/` for config-heavy scripts
9. Core skills: `/lit-guide`, `/lit-plan`, `/lit-validate`, `/lit-cite`, `/lit-search`, `/lit-acquire`
10. Pipeline skills: `/lit-extract`, `/lit-crawl`, `/lit-status`, `/lit-run`
11. Agents: `lit-abstract-reviewer`, `lit-triager`
12. Update `marketplace.json` in `.claude-plugin/`
13. Migration: `/lit-plan` for `bayesflow_irt_article` (generates config from old scripts)

---

## Verification

### Happy path
1. `/lit-validate 10.1145/3292500.3330701` — matches existing `bayesflow_hpo/docs/references.md` Akiba entry
2. `/lit-cite 10.1145/3292500.3330701` — APA 7 output matches manual version; `authors` list populated, `authors_str` and `apa7` fields correct
3. `/lit-acquire` for a Zotero-held paper — finds via SQLite, copies PDF, updates `_index.json` with `pdf` path
4. Full pipeline for `bayesflow_irt_article` A6-A8 — output consistent with existing artifacts
5. Auto-generated `references.md` from `_index.json` — diffs cleanly against existing `bayesflow_hpo/docs/references.md`

### Failure / edge cases
6. `/lit-validate` on an unknown DOI — returns not-found cleanly, no crash, no partial write to `_index.json`
7. `/lit-cite` for a paper already in `_index.json` — duplicate detected via `find_by_doi`, existing entry returned without overwrite
8. APA 7 formatting for a preprint (arXiv) and a book chapter — `format_apa7()` selects correct template by publication type
9. `/lit-acquire` for a paper not in Zotero and not OA — all fallbacks exhausted, failure reported with actionable message
10. `generate_citekey` collision (two papers with same first-author last name and year) — disambiguated with `a`/`b` suffix

### Non-IRT bootstrap
11. `/lit-plan` run from scratch in `bayesflow_hpo` — scaffolds `litreview.yaml`, `litreview/` directory, and `_index.json` from existing `docs/references.md`; no IRT-specific config required

---

## Review Notes

Adversarial review conducted 2026-04-04. All findings resolved in this document.

| # | Severity | Finding | Resolution |
|---|----------|---------|------------|
| 1 | High | No `agents/` directory or discovery story | Added `agents/` to plugin structure; agents section now specifies path resolution via `<plugin-path>/agents/<name>.md` |
| 2 | High | `_index.json` authors stored as string, not list; pipe-delimited source; single category | Schema updated: `authors` is now a list, `authors_str` holds APA-formatted string, `source` is a list, `categories` is a list |
| 3 | Medium | WSL paths implied but not scoped | Explicitly scoped to WSL POSIX paths only; native Windows paths not supported |
| 4 | Medium | Verification too narrow — no failure cases or non-IRT bootstrap | Expanded to 11 checks covering failure modes, APA edge cases, duplicate handling, and `bayesflow_hpo` bootstrap |
| 5 | Low | Skill count said 11 but only 10 defined | Corrected to "10 total" |

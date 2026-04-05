---
name: lit-latex
description: Export and validate LaTeX-safe BibTeX from `_index.json`.
---

# lit-latex

Use this skill when the user needs a `references.bib`, wants to lint BibTeX formatting, resolve citekeys, check a `.tex` file against a bibliography, or run a smoke compile.

Commands:

```bash
python scientific-literature/scripts/latex.py export-bib --index "<references_dir>/_index.json" --output "<project>/references.bib"
python scientific-literature/scripts/latex.py lint-bib --index "<references_dir>/_index.json"
python scientific-literature/scripts/latex.py citekey "<doi-or-title>" --index "<references_dir>/_index.json"
python scientific-literature/scripts/latex.py check-tex --tex "<project>/paper.tex" --bib "<project>/references.bib"
python scientific-literature/scripts/latex.py smoke-compile --bib "<project>/references.bib"
python scientific-literature/scripts/latex.py add-by-doi "<doi>" --index "<references_dir>/_index.json" --references-md "<references_md>" --output "<project>/references.bib"
```

Rules:
- `_index.json` remains the canonical source of metadata and citekeys.
- Write `references.bib` to a temp file first and replace the real file only if validation passes.
- Treat malformed author lists, unbalanced braces, duplicate citekeys, and missing required fields as hard failures.
- Allow deterministic auto-fixes such as LaTeX escaping, citekey sanitization, and title-case protection.

# BibTeX Reference

`references.bib` is derived from `_index.json`. Do not treat the `.bib` file as the primary data store.

## Export Rules

- Reuse `_index.json` citekeys. Do not invent separate LaTeX-only keys.
- Escape LaTeX-sensitive characters in text fields: `& % $ # _ { } ~ ^ \`.
- Protect capitalization in titles for acronyms, mixed-case tokens, and alphanumeric model names.
- Join authors with ` and ` in the final BibTeX output.
- Infer a BibTeX entry type from normalized metadata:
  - `article`
  - `inproceedings`
  - `book`
  - `incollection`
  - `phdthesis`
  - `techreport`
  - `misc`

## Hard Failures

- Invalid or duplicate citekeys
- Unbalanced braces
- Malformed or empty author fields
- Missing required fields for the inferred entry type

## Warnings

- Sparse metadata for preprints
- Unicode that may require BibLaTeX or XeLaTeX rather than plain BibTeX
- Ambiguous entry type inference

## Commands

```bash
python scientific-literature/scripts/latex.py export-bib --index "<references_dir>/_index.json" --output "<project>/references.bib"
python scientific-literature/scripts/latex.py lint-bib --index "<references_dir>/_index.json"
python scientific-literature/scripts/latex.py check-tex --tex "<project>/paper.tex" --bib "<project>/references.bib"
python scientific-literature/scripts/latex.py smoke-compile --bib "<project>/references.bib"
python scientific-literature/scripts/verify_latex.py --index scientific-literature/examples/latex/sample_index.json --tex scientific-literature/examples/latex/sample.tex --output scientific-literature/examples/latex/references.bib
```

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from bibtex import check_tex_against_bib, render_bibtex_file
from reference_index import ReferenceIndex


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify lit-latex behavior against local fixtures.")
    parser.add_argument("--index", required=True)
    parser.add_argument("--tex", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()

    index = ReferenceIndex(args.index)
    bib_contents, issues = render_bibtex_file(index.data)
    tex_contents = Path(args.tex).read_text(encoding="utf-8")
    tex_report = check_tex_against_bib(tex_contents, bib_contents)

    payload = {
        "status": "ok" if not _fatal_issues(issues) and not tex_report["missing_in_bib"] else "error",
        "entry_count": len(index.data),
        "issues": issues,
        "tex_report": tex_report,
        "checks": _run_content_checks(bib_contents, index.data),
    }

    payload["status"] = "ok" if _passes(payload) else "error"

    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(bib_contents, encoding="utf-8")
        payload["output"] = str(output)

    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if payload["status"] == "ok" else 1


def _fatal_issues(issues: list[str]) -> list[str]:
    return [issue for issue in issues if "ERROR:" in issue]


def _passes(payload: dict[str, object]) -> bool:
    if _fatal_issues(payload["issues"]):  # type: ignore[index]
        return False
    tex_report = payload["tex_report"]  # type: ignore[assignment]
    if tex_report["missing_in_bib"]:  # type: ignore[index]
        return False
    checks = payload["checks"]  # type: ignore[assignment]
    return all(v for v in checks.values() if isinstance(v, bool))  # type: ignore[union-attr]


def _run_content_checks(bib_contents: str, entries: dict[str, dict[str, object]]) -> dict[str, object]:
    """Derive checks from index metadata rather than hardcoding fixture values."""
    import re

    checks: dict[str, object] = {}

    # Verify every citekey appears as a BibTeX entry
    for citekey in entries:
        checks[f"entry_present:{citekey}"] = f"@" in bib_contents and f"{{{citekey}," in bib_contents

    # Verify LaTeX-special characters in metadata are escaped in output
    special_chars = {"&": r"\&", "%": r"\%", "_": r"\_"}
    for citekey, meta in entries.items():
        title = str(meta.get("title") or "")
        for raw, escaped in special_chars.items():
            if raw in title:
                checks[f"escaped_{raw}_in:{citekey}"] = escaped in bib_contents

    # Verify title-case protection for acronyms / mixed-case tokens
    acronym_pattern = re.compile(r"\b[A-Z][A-Za-z]*[0-9]+[A-Za-z]*\b|\b[A-Z]{2,}\b")
    for citekey, meta in entries.items():
        title = str(meta.get("title") or "")
        for match in acronym_pattern.finditer(title):
            token = match.group(0)
            checks[f"protected:{token}_in:{citekey}"] = "{" + token + "}" in bib_contents

    # Verify arXiv entries have eprint fields
    for citekey, meta in entries.items():
        arxiv_id = meta.get("arxiv_id")
        if arxiv_id:
            checks[f"arxiv_eprint:{citekey}"] = f"eprint = {{{arxiv_id}}}" in bib_contents

    return checks


if __name__ == "__main__":
    raise SystemExit(main())

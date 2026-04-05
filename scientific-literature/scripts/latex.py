from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from apa7 import format_apa7, format_authors_apa7, metadata_from_openalex
from bibtex import check_tex_against_bib, render_bibtex_file, smoke_compile_bib
from openalex import resolve_doi
from reference_index import ReferenceIndex


def main() -> int:
    parser = argparse.ArgumentParser(description="LaTeX/BibTeX helpers for scientific-literature.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    export_parser = subparsers.add_parser("export-bib", help="Export references.bib from _index.json.")
    export_parser.add_argument("--index", required=True)
    export_parser.add_argument("--output", required=True)
    export_parser.add_argument("--allow-warnings", action="store_true")

    lint_parser = subparsers.add_parser("lint-bib", help="Lint a BibTeX file or derived _index.json export.")
    lint_parser.add_argument("--index")
    lint_parser.add_argument("--input")
    lint_parser.add_argument("--allow-warnings", action="store_true")

    citekey_parser = subparsers.add_parser("citekey", help="Resolve DOI or title to a citekey.")
    citekey_parser.add_argument("identifier")
    citekey_parser.add_argument("--index", required=True)

    tex_parser = subparsers.add_parser("check-tex", help="Compare cite commands in a .tex file against a bibliography.")
    tex_parser.add_argument("--tex", required=True)
    tex_parser.add_argument("--index")
    tex_parser.add_argument("--bib")

    smoke_parser = subparsers.add_parser("smoke-compile", help="Run a temporary LaTeX compile against a bibliography.")
    smoke_parser.add_argument("--index")
    smoke_parser.add_argument("--bib")

    add_parser = subparsers.add_parser("add-by-doi", help="Add a DOI to _index.json and refresh bibliography outputs.")
    add_parser.add_argument("doi")
    add_parser.add_argument("--index", required=True)
    add_parser.add_argument("--references-md")
    add_parser.add_argument("--output")
    add_parser.add_argument("--allow-warnings", action="store_true")

    args = parser.parse_args()

    if args.command == "export-bib":
        return command_export_bib(args.index, args.output, args.allow_warnings)
    if args.command == "lint-bib":
        return command_lint_bib(args.index, args.input, args.allow_warnings)
    if args.command == "citekey":
        return command_citekey(args.identifier, args.index)
    if args.command == "check-tex":
        return command_check_tex(args.tex, args.index, args.bib)
    if args.command == "smoke-compile":
        return command_smoke_compile(args.index, args.bib)
    if args.command == "add-by-doi":
        return command_add_by_doi(
            doi=args.doi,
            index_path=args.index,
            references_md=args.references_md,
            bib_output=args.output,
            allow_warnings=args.allow_warnings,
        )
    parser.error(f"Unknown command: {args.command}")
    return 2


def command_export_bib(index_path: str, output_path: str, allow_warnings: bool) -> int:
    index = ReferenceIndex(index_path)
    contents, issues = render_bibtex_file(index.data)
    fatal = _blocking_issues(issues, allow_warnings=allow_warnings)
    if fatal:
        print(json.dumps({"status": "error", "issues": issues}, indent=2, ensure_ascii=False))
        return 1

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    temp_path = output.with_suffix(output.suffix + ".tmp")
    temp_path.write_text(contents, encoding="utf-8")
    temp_path.replace(output)
    print(
        json.dumps(
            {
                "status": "ok",
                "output": str(output),
                "entries": len(index.data),
                "issues": issues,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


def command_lint_bib(index_path: str | None, input_path: str | None, allow_warnings: bool) -> int:
    if bool(index_path) == bool(input_path):
        raise SystemExit("Specify exactly one of --index or --input for lint-bib.")

    if index_path:
        index = ReferenceIndex(index_path)
        _, issues = render_bibtex_file(index.data)
    else:
        contents = Path(input_path).read_text(encoding="utf-8")
        from bibtex import validate_bibtex_file

        issues = validate_bibtex_file(contents)

    status = "ok" if not _blocking_issues(issues, allow_warnings=allow_warnings) else "error"
    print(json.dumps({"status": status, "issues": issues}, indent=2, ensure_ascii=False))
    return 0 if status == "ok" else 1


def command_citekey(identifier: str, index_path: str) -> int:
    index = ReferenceIndex(index_path)
    existing = None
    if _looks_like_doi(identifier):
        existing = index.find_by_doi(identifier)
        if existing:
            citekey, entry = existing
            print(json.dumps({"status": "exists", "citekey": citekey, "entry": entry}, indent=2, ensure_ascii=False))
            return 0

        work = resolve_doi(identifier)
        if work:
            metadata = metadata_from_openalex(work)
            suggested = index.generate_citekey(metadata.get("authors", []), int(metadata.get("year") or 0))
            print(
                json.dumps(
                    {
                        "status": "suggested",
                        "citekey": suggested,
                        "metadata": metadata,
                    },
                    indent=2,
                    ensure_ascii=False,
                )
            )
            return 0
    existing = index.find_by_title(identifier)
    if existing:
        citekey, entry = existing
        print(json.dumps({"status": "exists", "citekey": citekey, "entry": entry}, indent=2, ensure_ascii=False))
        return 0

    print(json.dumps({"status": "not_found", "identifier": identifier}, indent=2, ensure_ascii=False))
    return 1


def command_check_tex(tex_path: str, index_path: str | None, bib_path: str | None) -> int:
    if bool(index_path) == bool(bib_path):
        raise SystemExit("Specify exactly one of --index or --bib for check-tex.")

    tex_text = Path(tex_path).read_text(encoding="utf-8")
    bib_contents = _load_bib_contents(index_path=index_path, bib_path=bib_path)
    result = check_tex_against_bib(tex_text, bib_contents)
    result["status"] = "ok" if not result["missing_in_bib"] else "error"
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if not result["missing_in_bib"] else 1


def command_smoke_compile(index_path: str | None, bib_path: str | None) -> int:
    if bool(index_path) == bool(bib_path):
        raise SystemExit("Specify exactly one of --index or --bib for smoke-compile.")

    bib_contents = _load_bib_contents(index_path=index_path, bib_path=bib_path)
    result = smoke_compile_bib(bib_contents)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("status") in {"ok", "skipped"} else 1


def command_add_by_doi(
    doi: str,
    index_path: str,
    references_md: str | None,
    bib_output: str | None,
    allow_warnings: bool,
) -> int:
    index = ReferenceIndex(index_path)
    existing = index.find_by_doi(doi)
    if existing:
        citekey, entry = existing
        payload: dict[str, Any] = {"status": "exists", "citekey": citekey, "entry": entry}
        if bib_output:
            export_status = _export_bib_after_index_change(index, bib_output, allow_warnings)
            payload["bib"] = export_status
            if export_status["status"] == "error":
                print(json.dumps(payload, indent=2, ensure_ascii=False))
                return 1
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    work = resolve_doi(doi)
    if not work:
        print(json.dumps({"status": "not_found", "doi": doi}, indent=2, ensure_ascii=False))
        return 1

    metadata = metadata_from_openalex(work)
    citekey = index.generate_citekey(metadata.get("authors", []), int(metadata.get("year") or 0))
    entry = {
        "title": metadata["title"],
        "authors": metadata["authors"],
        "authors_str": format_authors_apa7(metadata["authors"]),
        "year": metadata["year"],
        "journal": metadata.get("journal"),
        "booktitle": metadata.get("booktitle"),
        "publisher": metadata.get("publisher"),
        "pages": metadata.get("pages"),
        "volume": metadata.get("volume"),
        "issue": metadata.get("issue"),
        "doi": metadata.get("doi"),
        "type": metadata.get("type"),
        "url": metadata.get("url"),
        "arxiv_id": metadata.get("arxiv_id"),
        "note": metadata.get("note"),
        "openalex_id": work.get("id"),
        "categories": [],
        "source": [],
        "pdf": None,
        "apa7": format_apa7(metadata),
    }
    trial_data = copy.deepcopy(index.data)
    trial_data[citekey] = entry

    payload = {"status": "added", "citekey": citekey, "entry": entry}
    if bib_output:
        bib_result = _validate_bib_export(trial_data, allow_warnings)
        payload["bib"] = bib_result
        if bib_result["status"] == "error":
            print(json.dumps(payload, indent=2, ensure_ascii=False))
            return 1

    index.add(citekey, entry)

    if references_md:
        index.to_references_md(references_md)

    if bib_output:
        _write_bib_contents(bib_output, payload["bib"]["contents"])
        payload["bib"].pop("contents", None)

    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def _load_bib_contents(index_path: str | None, bib_path: str | None) -> str:
    if index_path:
        index = ReferenceIndex(index_path)
        contents, issues = render_bibtex_file(index.data)
        fatal = _blocking_issues(issues, allow_warnings=False)
        if fatal:
            raise SystemExit(json.dumps({"status": "error", "issues": issues}, indent=2, ensure_ascii=False))
        return contents
    return Path(bib_path).read_text(encoding="utf-8")


def _export_bib_after_index_change(index: ReferenceIndex, output_path: str, allow_warnings: bool) -> dict[str, Any]:
    result = _validate_bib_export(index.data, allow_warnings)
    if result["status"] == "error":
        return result
    _write_bib_contents(output_path, result["contents"])
    result.pop("contents", None)
    result["output"] = str(Path(output_path))
    return result


def _blocking_issues(issues: list[str], allow_warnings: bool) -> list[str]:
    errors = [issue for issue in issues if "ERROR:" in issue]
    if errors:
        return errors
    if allow_warnings:
        return []
    return [issue for issue in issues if "WARN:" in issue]


def _looks_like_doi(value: str) -> bool:
    lowered = value.strip().lower()
    return lowered.startswith("10.") or lowered.startswith("https://doi.org/") or lowered.startswith("http://doi.org/")


def _validate_bib_export(entries: dict[str, dict[str, Any]], allow_warnings: bool) -> dict[str, Any]:
    contents, issues = render_bibtex_file(entries)
    if _blocking_issues(issues, allow_warnings=allow_warnings):
        return {"status": "error", "issues": issues}
    return {"status": "ok", "issues": issues, "contents": contents}


def _write_bib_contents(output_path: str, contents: str) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    temp_path = output.with_suffix(output.suffix + ".tmp")
    temp_path.write_text(contents, encoding="utf-8")
    temp_path.replace(output)


if __name__ == "__main__":
    raise SystemExit(main())

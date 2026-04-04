from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from apa7 import format_apa7, format_authors_apa7, metadata_from_openalex
from openalex import resolve_doi
from reference_index import ReferenceIndex


def main() -> int:
    parser = argparse.ArgumentParser(description="Create or update citation entry from DOI.")
    parser.add_argument("doi")
    parser.add_argument("--index", required=True)
    parser.add_argument("--references-md", required=True)
    args = parser.parse_args()

    index = ReferenceIndex(args.index)
    existing = index.find_by_doi(args.doi)
    if existing:
        key, entry = existing
        print(json.dumps({"status": "exists", "citekey": key, "entry": entry}, indent=2, ensure_ascii=False))
        return 0

    work = resolve_doi(args.doi)
    if not work:
        print(json.dumps({"status": "not_found", "doi": args.doi}, indent=2))
        return 1

    metadata = metadata_from_openalex(work)
    citation = format_apa7(metadata)
    citekey = index.generate_citekey(metadata.get("authors", []), int(metadata.get("year") or 0))
    entry = {
        "title": metadata["title"],
        "authors": metadata["authors"],
        "authors_str": format_authors_apa7(metadata["authors"]),
        "year": metadata["year"],
        "journal": metadata.get("journal"),
        "doi": metadata.get("doi"),
        "openalex_id": work.get("id"),
        "categories": [],
        "source": [],
        "pdf": None,
        "apa7": citation,
    }
    index.add(citekey, entry)
    index.to_references_md(args.references_md)
    print(json.dumps({"status": "added", "citekey": citekey, "apa7": citation}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

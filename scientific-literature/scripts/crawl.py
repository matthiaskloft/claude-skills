from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from openalex import extract_work_info, get_references, resolve_doi


def main() -> int:
    parser = argparse.ArgumentParser(description="Crawl references from a DOI seed.")
    parser.add_argument("doi")
    parser.add_argument("--max-results", type=int, default=50)
    args = parser.parse_args()

    seed = resolve_doi(args.doi)
    if not seed:
        print(json.dumps({"status": "not_found", "doi": args.doi}, indent=2))
        return 1
    refs = get_references(seed["id"], max_results=args.max_results)
    print(json.dumps({"status": "ok", "seed": extract_work_info(seed), "references": [extract_work_info(item) for item in refs]}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

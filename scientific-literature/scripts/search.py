from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from openalex import extract_work_info, openalex_search


def main() -> int:
    parser = argparse.ArgumentParser(description="Search OpenAlex by keyword query.")
    parser.add_argument("query")
    parser.add_argument("--filter", default="")
    parser.add_argument("--per-page", type=int, default=20)
    parser.add_argument("--max-pages", type=int, default=2)
    args = parser.parse_args()

    works = openalex_search(args.query, filters=args.filter or None, per_page=args.per_page, max_pages=args.max_pages)
    normalized = [extract_work_info(work) for work in works]
    print(json.dumps(normalized, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

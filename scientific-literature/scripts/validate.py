from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from apa7 import format_apa7, metadata_from_openalex
from openalex import resolve_doi


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate DOI against OpenAlex.")
    parser.add_argument("doi")
    args = parser.parse_args()

    work = resolve_doi(args.doi)
    if not work:
        print(json.dumps({"found": False, "doi": args.doi}, indent=2))
        return 1
    metadata = metadata_from_openalex(work)
    payload = {"found": True, "metadata": metadata, "apa7": format_apa7(metadata)}
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

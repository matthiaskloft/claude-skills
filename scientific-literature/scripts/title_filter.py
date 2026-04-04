from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import yaml


def main() -> int:
    parser = argparse.ArgumentParser(description="Filter titles by configured regex patterns.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--input", required=True)
    args = parser.parse_args()

    patterns = yaml.safe_load(Path(args.config).read_text(encoding="utf-8")).get("include_patterns", [])
    titles = json.loads(Path(args.input).read_text(encoding="utf-8"))
    compiled = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    filtered = [title for title in titles if any(regex.search(title) for regex in compiled)]
    print(json.dumps(filtered, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

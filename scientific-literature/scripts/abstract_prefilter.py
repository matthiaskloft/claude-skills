from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml


def _score(text: str, keywords: list[str]) -> int:
    lowered = text.lower()
    return sum(1 for keyword in keywords if keyword.lower() in lowered)


def main() -> int:
    parser = argparse.ArgumentParser(description="Keyword-based abstract prefilter.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--input", required=True)
    args = parser.parse_args()

    config = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    include = config.get("include_keywords", [])
    records = json.loads(Path(args.input).read_text(encoding="utf-8"))
    scored = []
    for record in records:
        score = _score(record.get("abstract", ""), include)
        record["prefilter_score"] = score
        if score > 0:
            scored.append(record)
    print(json.dumps(scored, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

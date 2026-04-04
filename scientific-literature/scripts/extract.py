from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from pdf_extract import build_skeleton, detect_sections, extract_pdf, sections_to_markdown


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract and section a PDF into markdown.")
    parser.add_argument("pdf")
    parser.add_argument("--output", required=True)
    parser.add_argument("--title", default="Untitled")
    args = parser.parse_args()

    text, pages = extract_pdf(args.pdf)
    sections = detect_sections(text)
    skeleton = build_skeleton(sections)
    markdown = sections_to_markdown(sections, {"title": args.title})
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
    print(json.dumps({"status": "ok", "pages": pages, "sections": len(sections), "skeleton": skeleton}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

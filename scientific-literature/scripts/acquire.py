from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from arxiv_client import arxiv_search, download_pdf
from openalex import get_oa_url
from zotero_local import ZoteroSearch, load_local_cache


def main() -> int:
    parser = argparse.ArgumentParser(description="Acquire full text via Zotero/OpenAlex/arXiv.")
    parser.add_argument("--title", required=True)
    parser.add_argument("--doi", default="")
    parser.add_argument("--openalex-id", default="")
    parser.add_argument("--dest", required=True)
    parser.add_argument("--cache", default=".lit-cache.json")
    args = parser.parse_args()

    dest = Path(args.dest)
    dest.mkdir(parents=True, exist_ok=True)
    cache = load_local_cache(args.cache)
    zotero = ZoteroSearch(cache)

    source_path, meta = zotero.search(title=args.title, doi=args.doi or None)
    if source_path:
        target = dest / Path(source_path).name
        shutil.copy2(source_path, target)
        print(json.dumps({"status": "ok", "method": "zotero", "path": str(target), "meta": meta}, indent=2))
        return 0

    if args.openalex_id:
        oa_info = get_oa_url(args.openalex_id)
        pdf_url = oa_info.get("pdf_url")
        if pdf_url:
            target = dest / (Path(args.openalex_id).name + ".pdf")
            ok, details = download_pdf(pdf_url, str(target))
            if ok:
                print(json.dumps({"status": "ok", "method": "openalex_oa", "path": str(target), "bytes": details}, indent=2))
                return 0

    for candidate in arxiv_search(args.title, max_results=3):
        pdf_url = candidate.get("pdf_url")
        if not pdf_url:
            continue
        target = dest / (Path(candidate["id"]).name + ".pdf")
        ok, details = download_pdf(pdf_url, str(target))
        if ok:
            print(json.dumps({"status": "ok", "method": "arxiv", "path": str(target), "bytes": details}, indent=2))
            return 0

    print(json.dumps({"status": "not_found", "title": args.title}, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

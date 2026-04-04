"""Minimal arXiv client."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus
from xml.etree import ElementTree

import requests

ARXIV_API = "http://export.arxiv.org/api/query"


def arxiv_search(query: str, max_results: int = 3) -> list[dict[str, Any]]:
    url = f"{ARXIV_API}?search_query=all:{quote_plus(query)}&start=0&max_results={max_results}"
    response = requests.get(url, timeout=30, headers={"User-Agent": "scientific-literature/0.1.0"})
    response.raise_for_status()
    root = ElementTree.fromstring(response.text)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    entries = []
    for entry in root.findall("atom:entry", ns):
        pdf_url = ""
        for link in entry.findall("atom:link", ns):
            if link.attrib.get("type") == "application/pdf":
                pdf_url = link.attrib.get("href", "")
                break
        entries.append(
            {
                "id": entry.findtext("atom:id", default="", namespaces=ns),
                "title": entry.findtext("atom:title", default="", namespaces=ns).strip(),
                "summary": entry.findtext("atom:summary", default="", namespaces=ns).strip(),
                "pdf_url": pdf_url,
            }
        )
    return entries


def download_pdf(url: str, filepath: str) -> tuple[bool, int | str]:
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        response = requests.get(url, timeout=60, headers={"User-Agent": "scientific-literature/0.1.0"})
        response.raise_for_status()
    except requests.RequestException as exc:
        return False, str(exc)
    path.write_bytes(response.content)
    return True, len(response.content)


def download_tex_source(arxiv_id: str, dest_dir: str) -> str | None:
    clean_id = arxiv_id.rsplit("/", 1)[-1]
    clean_id = re.sub(r"v\d+$", "", clean_id)
    url = f"https://arxiv.org/e-print/{clean_id}"
    path = Path(dest_dir) / f"{clean_id}.tar"
    ok, _ = download_pdf(url, str(path))
    return str(path) if ok else None

"""Reference index read/write utilities."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


class ReferenceIndex:
    def __init__(self, index_path: str):
        self.path = Path(index_path)
        self.data = self._load()

    def _load(self) -> dict[str, Any]:
        if self.path.exists():
            return json.loads(self.path.read_text(encoding="utf-8"))
        return {}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8")

    def add(self, citekey: str, metadata: dict[str, Any]) -> None:
        enriched = dict(metadata)
        enriched.setdefault("added_at", datetime.now(timezone.utc).date().isoformat())
        self.data[citekey] = enriched
        self._save()

    def get(self, citekey: str) -> dict[str, Any] | None:
        return self.data.get(citekey)

    def find_by_doi(self, doi: str) -> tuple[str, dict[str, Any]] | None:
        target = _normalize_doi(doi)
        for key, value in self.data.items():
            existing = _normalize_doi(value.get("doi", ""))
            if existing and existing == target:
                return key, value
        return None

    def find_by_title(self, title: str, threshold: float = 0.8) -> tuple[str, dict[str, Any]] | None:
        target = title.strip().lower()
        best: tuple[str, dict[str, Any]] | None = None
        best_ratio = 0.0
        for key, value in self.data.items():
            ratio = SequenceMatcher(None, target, str(value.get("title", "")).lower()).ratio()
            if ratio >= threshold and ratio > best_ratio:
                best = (key, value)
                best_ratio = ratio
        return best

    def generate_citekey(self, authors: list[str], year: int) -> str:
        base_author = "unknown"
        if authors:
            base_author = re.sub(r"[^a-z0-9]+", "_", authors[0].split(",")[0].lower()).strip("_")
        base = f"{base_author}_{year}"
        if base not in self.data:
            return base
        suffix = "a"
        while f"{base}{suffix}" in self.data:
            suffix = chr(ord(suffix) + 1)
        return f"{base}{suffix}"

    def to_references_md(self, output_path: str) -> None:
        path = Path(output_path)
        lines = ["# References", ""]
        for _, entry in sorted(self.data.items(), key=lambda item: item[0]):
            citation = entry.get("apa7", "")
            if citation:
                lines.append(f"- {citation}")
        lines.append("")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines), encoding="utf-8")


def _normalize_doi(doi: str) -> str:
    normalized = doi.strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/"):
        if normalized.startswith(prefix):
            return normalized.removeprefix(prefix)
    return normalized

"""Zotero local search via SQLite and PDF fallback."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


class ZoteroSearch:
    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.sqlite_path = Path(config.get("zotero_sqlite", "")).expanduser()
        self.storage_path = Path(config.get("zotero_storage", "")).expanduser()
        self.articles_path = Path(config.get("zotero_articles", "")).expanduser()

    def search(self, title: str | None = None, doi: str | None = None) -> tuple[str | None, dict[str, Any]]:
        result = self._search_sqlite(title, doi)
        if result[0]:
            return result
        if title:
            pdf_path, score = self._scan_pdfs(title)
            if pdf_path:
                return pdf_path, {"method": "filename_scan", "score": score}
        return None, {"method": "none"}

    def _search_sqlite(self, title: str | None, doi: str | None) -> tuple[str | None, dict[str, Any]]:
        if not self.sqlite_path.exists():
            return None, {"method": "sqlite", "error": "sqlite_not_found"}
        query = """
        SELECT itemAttachments.path
        FROM items
        JOIN itemData ON itemData.itemID = items.itemID
        JOIN itemDataValues ON itemDataValues.valueID = itemData.valueID
        LEFT JOIN itemAttachments ON itemAttachments.parentItemID = items.itemID
        WHERE itemDataValues.value LIKE ?
        LIMIT 1
        """
        needle = f"%{doi or title or ''}%"
        try:
            with sqlite3.connect(str(self.sqlite_path)) as conn:
                row = conn.execute(query, (needle,)).fetchone()
        except sqlite3.Error as exc:
            return None, {"method": "sqlite", "error": str(exc)}
        if not row or not row[0]:
            return None, {"method": "sqlite", "match": False}
        relative = row[0].replace("storage:", "")
        candidate = self.storage_path / relative
        if candidate.exists():
            return str(candidate), {"method": "sqlite", "match": True}
        return None, {"method": "sqlite", "match": False}

    def _scan_pdfs(self, title: str) -> tuple[str | None, float]:
        normalized = set(_tokens(title))
        best_path: str | None = None
        best_score = 0.0
        for base in [self.storage_path, self.articles_path]:
            if not base.exists():
                continue
            for pdf in base.rglob("*.pdf"):
                tokens = set(_tokens(pdf.stem))
                if not tokens:
                    continue
                score = len(normalized & tokens) / max(1, len(normalized))
                if score > best_score:
                    best_score = score
                    best_path = str(pdf)
        return best_path, best_score


def _tokens(value: str) -> list[str]:
    return [token.lower() for token in value.replace("_", " ").replace("-", " ").split() if len(token) > 2]


def load_local_cache(cache_path: str) -> dict[str, Any]:
    path = Path(cache_path)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))

"""OpenAlex API helpers."""

from __future__ import annotations

from typing import Any

import requests

OPENALEX_BASE = "https://api.openalex.org"
DEFAULT_SELECT = [
    "id",
    "doi",
    "title",
    "publication_year",
    "type",
    "primary_location",
    "authorships",
    "host_venue",
    "biblio",
    "abstract_inverted_index",
    "referenced_works_count",
    "cited_by_count",
]


def _request(endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    response = requests.get(
        f"{OPENALEX_BASE}{endpoint}",
        params=params,
        timeout=30,
        headers={"User-Agent": "scientific-literature/0.1.0"},
    )
    response.raise_for_status()
    return response.json()


def reconstruct_abstract(inverted_index: dict[str, list[int]] | None) -> str:
    """Rebuild a plain text abstract from OpenAlex inverted index."""
    if not inverted_index:
        return ""
    pairs: list[tuple[int, str]] = []
    for token, positions in inverted_index.items():
        for position in positions:
            pairs.append((position, token))
    pairs.sort(key=lambda item: item[0])
    return " ".join(token for _, token in pairs)


def extract_work_info(work: dict[str, Any]) -> dict[str, Any]:
    """Normalize a work record to stable downstream fields."""
    authors = []
    for authorship in work.get("authorships", []):
        author = authorship.get("author", {})
        name = author.get("display_name")
        if name:
            authors.append(name)
    location = work.get("primary_location") or {}
    source = location.get("source") or {}
    return {
        "openalex_id": work.get("id"),
        "doi": work.get("doi"),
        "title": work.get("title", ""),
        "year": work.get("publication_year"),
        "type": work.get("type"),
        "authors": authors,
        "venue": source.get("display_name") or work.get("host_venue", {}).get("display_name"),
        "cited_by_count": work.get("cited_by_count"),
        "referenced_works_count": work.get("referenced_works_count"),
        "is_oa": bool(location.get("is_oa")),
        "oa_url": (location.get("landing_page_url") or location.get("pdf_url")),
        "abstract": reconstruct_abstract(work.get("abstract_inverted_index")),
    }


def openalex_search(
    query: str,
    filters: str | None = None,
    per_page: int = 50,
    max_pages: int = 4,
    select: list[str] | None = None,
) -> list[dict[str, Any]]:
    works: list[dict[str, Any]] = []
    fields = ",".join(select or DEFAULT_SELECT)
    for page in range(1, max_pages + 1):
        params: dict[str, Any] = {
            "search": query,
            "per-page": per_page,
            "page": page,
            "select": fields,
        }
        if filters:
            params["filter"] = filters
        data = _request("/works", params=params)
        page_results = data.get("results", [])
        works.extend(page_results)
        if len(page_results) < per_page:
            break
    return works


def openalex_filter_search(
    title_keywords: str,
    author_name: str,
    extra_filters: str = "",
    per_page: int = 5,
) -> list[dict[str, Any]]:
    clauses = [f"title.search:{title_keywords}", f"authorships.author.display_name.search:{author_name}"]
    if extra_filters:
        clauses.append(extra_filters)
    return openalex_search(
        query=title_keywords,
        filters=",".join(clauses),
        per_page=per_page,
        max_pages=1,
    )


def resolve_doi(doi: str) -> dict[str, Any] | None:
    normalized = doi.strip()
    if not normalized:
        return None
    if normalized.startswith("https://doi.org/"):
        normalized = normalized.removeprefix("https://doi.org/")
    if normalized.startswith("http://doi.org/"):
        normalized = normalized.removeprefix("http://doi.org/")
    try:
        data = _request("/works", params={"filter": f"doi:{normalized}", "per-page": 1})
    except requests.HTTPError:
        return None
    results = data.get("results", [])
    return results[0] if results else None


def get_oa_url(openalex_id: str) -> dict[str, Any]:
    work = _request(f"/works/{openalex_id.split('/')[-1]}")
    location = work.get("primary_location") or {}
    return {
        "landing_page_url": location.get("landing_page_url"),
        "pdf_url": location.get("pdf_url"),
        "is_oa": bool(location.get("is_oa")),
    }


def get_citations(openalex_id: str, max_results: int = 200) -> list[dict[str, Any]]:
    normalized = openalex_id if openalex_id.startswith("https://openalex.org/") else f"https://openalex.org/{openalex_id}"
    data = _request(
        "/works",
        params={
            "filter": f"cites:{normalized}",
            "per-page": min(max_results, 200),
            "page": 1,
        },
    )
    return data.get("results", [])


def get_references(openalex_id: str, max_results: int = 200) -> list[dict[str, Any]]:
    work = _request(f"/works/{openalex_id.split('/')[-1]}")
    ids = work.get("referenced_works", [])[:max_results]
    if not ids:
        return []
    related: list[dict[str, Any]] = []
    for chunk_start in range(0, len(ids), 25):
        chunk = ids[chunk_start : chunk_start + 25]
        data = _request("/works", params={"filter": f"openalex:{'|'.join(chunk)}", "per-page": len(chunk)})
        related.extend(data.get("results", []))
    return related

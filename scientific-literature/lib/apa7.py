"""APA7 formatting utilities."""

from __future__ import annotations

import re
from typing import Any


def format_authors_apa7(authors: list[str]) -> str:
    if not authors:
        return ""
    if len(authors) == 1:
        return authors[0]
    if len(authors) == 2:
        return f"{authors[0]}, & {authors[1]}"
    return ", ".join(authors[:-1]) + f", & {authors[-1]}"


def metadata_from_openalex(work: dict[str, Any]) -> dict[str, Any]:
    raw_authors = []
    for authorship in work.get("authorships", []):
        name = (authorship.get("author") or {}).get("display_name")
        if name:
            raw_authors.append(name)
    primary_location = work.get("primary_location") or {}
    source = primary_location.get("source") or {}
    host_venue = work.get("host_venue") or {}
    biblio = work.get("biblio") or {}
    first = biblio.get("first_page")
    last = biblio.get("last_page")
    pages = f"{first}-{last}" if first and last else (first or "")
    source_name = source.get("display_name") or host_venue.get("display_name")
    work_type = work.get("type")
    is_conference = str(work_type or "").lower() in {"conference", "proceedings-article"}
    landing_url = primary_location.get("landing_page_url") or primary_location.get("pdf_url") or work.get("doi")
    arxiv_id = _extract_arxiv_id(work)
    return {
        "title": work.get("title", ""),
        "authors": raw_authors,
        "year": work.get("publication_year"),
        "doi": work.get("doi"),
        "journal": None if is_conference else source_name,
        "booktitle": source_name if is_conference else None,
        "publisher": source.get("host_organization_name") or host_venue.get("publisher"),
        "volume": biblio.get("volume"),
        "issue": biblio.get("issue"),
        "pages": pages,
        "type": work_type,
        "url": landing_url,
        "arxiv_id": arxiv_id,
        "note": "Preprint" if str(work_type or "").lower() == "preprint" else None,
    }


def format_apa7(metadata: dict[str, Any]) -> str:
    authors = format_authors_apa7(metadata.get("authors", []))
    year = metadata.get("year") or "n.d."
    title = metadata.get("title", "").rstrip(".")
    journal = metadata.get("journal") or metadata.get("booktitle") or ""
    volume = metadata.get("volume") or ""
    issue = metadata.get("issue") or ""
    pages = metadata.get("pages") or ""
    doi = metadata.get("doi") or ""
    volume_issue = ""
    if volume and issue:
        volume_issue = f"{volume}({issue})"
    elif volume:
        volume_issue = volume
    details = ", ".join(part for part in [journal, volume_issue, pages] if part)
    pieces = [f"{authors} ({year}). {title}."]
    if details:
        pieces.append(details + ".")
    if doi:
        pieces.append(doi if str(doi).startswith("http") else f"https://doi.org/{doi}")
    return " ".join(piece for piece in pieces if piece).strip()


def _extract_arxiv_id(work: dict[str, Any]) -> str | None:
    identifiers = work.get("ids") or {}
    for value in identifiers.values():
        extracted = _extract_arxiv_id_from_text(str(value))
        if extracted:
            return extracted

    primary_location = work.get("primary_location") or {}
    for candidate in (
        primary_location.get("landing_page_url"),
        primary_location.get("pdf_url"),
        work.get("doi"),
    ):
        extracted = _extract_arxiv_id_from_text(str(candidate or ""))
        if extracted:
            return extracted
    return None


def _extract_arxiv_id_from_text(value: str) -> str | None:
    if not value:
        return None
    patterns = [
        r"arxiv\.org/(?:abs|pdf)/([0-9]{4}\.[0-9]{4,5}(?:v\d+)?)",
        r"arxiv[:/ ]([0-9]{4}\.[0-9]{4,5}(?:v\d+)?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, value, flags=re.IGNORECASE)
        if match:
            return match.group(1)
    return None

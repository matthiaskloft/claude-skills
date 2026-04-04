"""APA7 formatting utilities."""

from __future__ import annotations

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
    biblio = work.get("biblio") or {}
    first = biblio.get("first_page")
    last = biblio.get("last_page")
    pages = f"{first}-{last}" if first and last else (first or "")
    return {
        "title": work.get("title", ""),
        "authors": raw_authors,
        "year": work.get("publication_year"),
        "doi": work.get("doi"),
        "journal": source.get("display_name"),
        "volume": biblio.get("volume"),
        "issue": biblio.get("issue"),
        "pages": pages,
        "type": work.get("type"),
    }


def format_apa7(metadata: dict[str, Any]) -> str:
    authors = format_authors_apa7(metadata.get("authors", []))
    year = metadata.get("year") or "n.d."
    title = metadata.get("title", "").rstrip(".")
    journal = metadata.get("journal") or ""
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

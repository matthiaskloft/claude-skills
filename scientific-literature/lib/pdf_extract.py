"""PDF extraction helpers."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

SECTION_PATTERNS = [
    re.compile(r"^(abstract)$", re.IGNORECASE),
    re.compile(r"^(introduction)$", re.IGNORECASE),
    re.compile(r"^(methods?|methodology)$", re.IGNORECASE),
    re.compile(r"^(results?)$", re.IGNORECASE),
    re.compile(r"^(discussion)$", re.IGNORECASE),
    re.compile(r"^(conclusion[s]?)$", re.IGNORECASE),
    re.compile(r"^(references|bibliography)$", re.IGNORECASE),
]


def extract_pdf(pdf_path: str) -> tuple[str, int]:
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(pdf_path)
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("pypdf is required for PDF extraction") from exc

    reader = PdfReader(str(path))
    text_parts: list[str] = []
    for page in reader.pages:
        text_parts.append(page.extract_text() or "")
    return "\n\n".join(text_parts), len(reader.pages)


def detect_sections(text: str) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    current_title = "Front Matter"
    current_lines: list[str] = []
    for line in text.splitlines():
        normalized = line.strip()
        if _is_section_title(normalized):
            if current_lines:
                sections.append({"title": current_title, "content": "\n".join(current_lines).strip()})
            current_title = normalized.title()
            current_lines = []
        else:
            current_lines.append(line)
    if current_lines:
        sections.append({"title": current_title, "content": "\n".join(current_lines).strip()})
    return [section for section in sections if section["content"]]


def _is_section_title(line: str) -> bool:
    if not line or len(line) > 60:
        return False
    return any(pattern.match(line) for pattern in SECTION_PATTERNS)


def build_skeleton(sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    skeleton = []
    for section in sections:
        words = section["content"].split()
        snippet = " ".join(words[:150])
        skeleton.append({"title": section["title"], "snippet": snippet, "word_count": len(words)})
    return skeleton


def build_category_extract(sections: list[dict[str, Any]], target_sections: list[str]) -> list[dict[str, Any]]:
    targets = {item.lower().strip() for item in target_sections}
    return [section for section in sections if section["title"].lower() in targets]


def sections_to_markdown(sections: list[dict[str, Any]], metadata: dict[str, Any]) -> str:
    title = metadata.get("title", "Untitled")
    lines = [f"# {title}", ""]
    for section in sections:
        lines.append(f"## {section['title']}")
        lines.append("")
        lines.append(section["content"])
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"

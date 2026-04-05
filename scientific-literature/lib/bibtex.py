"""BibTeX and LaTeX safety helpers for literature workflows."""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import unicodedata
from pathlib import Path
from typing import Any


ENTRY_TYPE_MAP = {
    "article": "article",
    "journal-article": "article",
    "conference": "inproceedings",
    "proceedings-article": "inproceedings",
    "book": "book",
    "book-chapter": "incollection",
    "chapter": "incollection",
    "dissertation": "phdthesis",
    "thesis": "phdthesis",
    "report": "techreport",
    "preprint": "misc",
}

REQUIRED_FIELDS = {
    "article": ("title", "author", "journal", "year"),
    "inproceedings": ("title", "author", "booktitle", "year"),
    "book": ("title", "author", "publisher", "year"),
    "incollection": ("title", "author", "booktitle", "year"),
    "phdthesis": ("title", "author", "school", "year"),
    "techreport": ("title", "author", "institution", "year"),
    "misc": ("title", "author", "year"),
}

TEXT_FIELDS = (
    "title",
    "journal",
    "booktitle",
    "publisher",
    "institution",
    "school",
    "series",
    "note",
)

LATEX_SPECIAL_CHARS = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}

CITE_PATTERN = re.compile(
    r"\\[A-Za-z]*cite[A-Za-z*]*"
    r"(?:\[[^\]]*\]){0,2}"
    r"\{([^}]*)\}"
)
ENTRY_KEY_PATTERN = re.compile(r"@\w+\s*\{\s*([^,\s]+)", re.IGNORECASE)
FIELD_PATTERN = re.compile(r"^\s*([A-Za-z][A-Za-z0-9]*)\s*=\s*\{(.*)\}\s*,?\s*$")


def infer_bibtex_type(metadata: dict[str, Any]) -> str:
    raw_type = str(metadata.get("type") or "").strip().lower()
    mapped = ENTRY_TYPE_MAP.get(raw_type)
    if mapped in {"incollection", "phdthesis", "techreport"}:
        return mapped
    if metadata.get("journal"):
        return mapped or "article"
    if metadata.get("booktitle"):
        return mapped or "inproceedings"
    if metadata.get("publisher"):
        return mapped or "book"
    if metadata.get("doi", "").startswith("https://arxiv.org/") or metadata.get("arxiv_id"):
        return "misc"
    return mapped or "misc"


def sanitize_citekey(citekey: str) -> str:
    normalized = unicodedata.normalize("NFKD", citekey)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    sanitized = re.sub(r"[^A-Za-z0-9._:-]+", "_", ascii_only).strip("._:-_")
    sanitized = re.sub(r"_+", "_", sanitized)
    return sanitized or "citation"


def escape_latex(text: str) -> str:
    pieces: list[str] = []
    for char in text:
        pieces.append(LATEX_SPECIAL_CHARS.get(char, char))
    return "".join(pieces)


def protect_title_case(title: str) -> str:
    if not title:
        return title

    def protect(match: re.Match[str]) -> str:
        token = match.group(0)
        if token.startswith("{") and token.endswith("}"):
            return token
        if token.isupper() and len(token) > 1:
            return "{" + token + "}"
        if any(ch.isdigit() for ch in token) and any(ch.isalpha() for ch in token):
            return "{" + token + "}"
        if re.search(r"[a-z][A-Z]", token):
            return "{" + token + "}"
        return token

    return re.sub(r"\b[A-Za-z0-9][A-Za-z0-9:+./-]*\b", protect, title)


def format_bibtex_authors(authors: list[str]) -> str:
    cleaned = [author.strip() for author in authors if author and author.strip()]
    return " and ".join(cleaned)


def validate_bibtex_entry(citekey: str, metadata: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    sanitized = sanitize_citekey(citekey)
    if sanitized != citekey:
        issues.append(f"ERROR: citekey '{citekey}' is not BibTeX-safe; use '{sanitized}'")

    for field in TEXT_FIELDS:
        value = metadata.get(field)
        if value and not _has_balanced_braces(str(value)):
            issues.append(f"ERROR: field '{field}' has unbalanced braces")

    authors = metadata.get("authors", [])
    if authors is None:
        authors = []
    if not isinstance(authors, list):
        issues.append("ERROR: authors must be a list of strings")
    elif not format_bibtex_authors(authors):
        issues.append("ERROR: authors list is empty")

    entry_type = infer_bibtex_type(metadata)
    fields = _build_bibtex_fields(metadata, validate_only=True)
    for field in REQUIRED_FIELDS.get(entry_type, ()):
        value = fields.get(field)
        if not value:
            issues.append(f"ERROR: missing required field '{field}' for entry type '{entry_type}'")

    if metadata.get("doi") and "arxiv.org" in str(metadata.get("doi")).lower() and not metadata.get("arxiv_id"):
        issues.append("WARN: arXiv DOI detected without explicit arxiv_id metadata")

    if _contains_suspicious_unicode(metadata):
        issues.append("WARN: metadata contains non-ASCII characters; BibLaTeX/XeLaTeX may be safer than plain BibTeX")

    return issues


def metadata_to_bibtex_entry(citekey: str, metadata: dict[str, Any]) -> str:
    entry_type = infer_bibtex_type(metadata)
    fields = _build_bibtex_fields(metadata)
    ordered_fields = _ordered_fields(fields)
    lines = [f"@{entry_type}{{{sanitize_citekey(citekey)},"]
    for name, value in ordered_fields:
        lines.append(f"  {name} = {{{value}}},")
    if lines[-1].endswith(","):
        lines[-1] = lines[-1][:-1]
    lines.append("}")
    return "\n".join(lines)


def validate_bibtex_file(contents: str) -> list[str]:
    issues: list[str] = []
    if not _has_balanced_braces(contents):
        issues.append("ERROR: file has unbalanced braces")

    seen: set[str] = set()
    for key in ENTRY_KEY_PATTERN.findall(contents):
        if key in seen:
            issues.append(f"ERROR: duplicate citekey '{key}' in BibTeX file")
        seen.add(key)
        if sanitize_citekey(key) != key:
            issues.append(f"ERROR: citekey '{key}' is not BibTeX-safe")

    for line in contents.splitlines():
        match = FIELD_PATTERN.match(line)
        if not match:
            continue
        field_name = match.group(1).lower()
        value = match.group(2)
        if field_name == "author" and " and " not in value and "," in value:
            issues.append("WARN: author field may use commas instead of ' and ' separators")
        specials = _find_unescaped_special_chars(value)
        if specials:
            escaped = ", ".join(sorted(specials))
            issues.append(f"WARN: field '{field_name}' contains unescaped LaTeX-sensitive characters: {escaped}")
    return issues


def render_bibtex_file(entries: dict[str, dict[str, Any]]) -> tuple[str, list[str]]:
    issues: list[str] = []
    rendered: list[str] = []
    sanitized_seen: set[str] = set()

    for citekey, metadata in sorted(entries.items(), key=lambda item: item[0]):
        entry_issues = validate_bibtex_entry(citekey, metadata)
        issues.extend(f"{citekey}: {issue}" for issue in entry_issues)
        safe_citekey = sanitize_citekey(citekey)
        if safe_citekey in sanitized_seen:
            issues.append(f"{citekey}: ERROR: sanitized citekey '{safe_citekey}' collides with another entry")
            continue
        sanitized_seen.add(safe_citekey)
        rendered.append(metadata_to_bibtex_entry(citekey, metadata))

    contents = "\n\n".join(rendered) + ("\n" if rendered else "")
    issues.extend(validate_bibtex_file(contents))
    return contents, issues


def extract_citekeys_from_tex(text: str) -> set[str]:
    citekeys: set[str] = set()
    for match in CITE_PATTERN.finditer(text):
        group = match.group(1)
        for citekey in group.split(","):
            cleaned = citekey.strip()
            if cleaned:
                citekeys.add(cleaned)
    return citekeys


def check_tex_against_bib(tex_text: str, bib_contents: str) -> dict[str, list[str]]:
    cited = extract_citekeys_from_tex(tex_text)
    known = set(ENTRY_KEY_PATTERN.findall(bib_contents))
    return {
        "cited": sorted(cited),
        "missing_in_bib": sorted(cited - known),
        "unused_in_bib": sorted(known - cited),
    }


def smoke_compile_bib(bib_contents: str, tex_engine: str = "pdflatex", bib_engine: str = "bibtex") -> dict[str, Any]:
    if not shutil.which(tex_engine) or not shutil.which(bib_engine):
        return {
            "status": "skipped",
            "reason": f"required tools not found: {tex_engine}, {bib_engine}",
        }

    with tempfile.TemporaryDirectory(prefix="lit-latex-") as tmp_dir:
        tmp_path = Path(tmp_dir)
        bib_path = tmp_path / "references.bib"
        tex_path = tmp_path / "smoke.tex"
        bib_path.write_text(bib_contents, encoding="utf-8")
        tex_path.write_text(_smoke_tex_document(), encoding="utf-8")

        commands = [
            [tex_engine, "-interaction=nonstopmode", "smoke.tex"],
            [bib_engine, "smoke"],
            [tex_engine, "-interaction=nonstopmode", "smoke.tex"],
            [tex_engine, "-interaction=nonstopmode", "smoke.tex"],
        ]
        runs: list[dict[str, Any]] = []
        for command in commands:
            completed = subprocess.run(
                command,
                cwd=tmp_path,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            runs.append(
                {
                    "command": command,
                    "returncode": completed.returncode,
                    "stdout": completed.stdout[-4000:],
                    "stderr": completed.stderr[-4000:],
                }
            )
            if completed.returncode != 0:
                return {"status": "failed", "runs": runs}

        return {"status": "ok", "runs": runs}


def _build_bibtex_fields(metadata: dict[str, Any], validate_only: bool = False) -> dict[str, str]:
    authors = metadata.get("authors", [])
    if authors is None:
        authors = []
    values: dict[str, str] = {
        "author": format_bibtex_authors(authors if isinstance(authors, list) else []),
        "title": str(metadata.get("title") or ""),
        "year": str(metadata.get("year") or ""),
    }

    entry_type = infer_bibtex_type(metadata)
    container = str(metadata.get("journal") or metadata.get("booktitle") or "")
    if entry_type == "article":
        values["journal"] = container
    elif entry_type == "inproceedings":
        values["booktitle"] = container
    elif entry_type == "book":
        values["publisher"] = str(metadata.get("publisher") or "")
    elif entry_type == "incollection":
        values["booktitle"] = container
    elif entry_type == "phdthesis":
        values["school"] = str(metadata.get("school") or metadata.get("institution") or "")
    elif entry_type == "techreport":
        values["institution"] = str(metadata.get("institution") or "")

    optional_fields = {
        "volume": metadata.get("volume"),
        "number": metadata.get("issue"),
        "pages": metadata.get("pages"),
        "doi": _normalize_doi_url(str(metadata.get("doi") or "")),
        "url": metadata.get("url"),
        "note": metadata.get("note"),
        "publisher": metadata.get("publisher"),
        "series": metadata.get("series"),
    }

    arxiv_id = str(metadata.get("arxiv_id") or "")
    if arxiv_id:
        optional_fields["eprint"] = arxiv_id
        optional_fields["archivePrefix"] = "arXiv"

    for key, value in optional_fields.items():
        if value is None or value == "":
            continue
        values[key] = str(value)

    if validate_only:
        return {key: value.strip() for key, value in values.items()}

    escaped: dict[str, str] = {}
    for key, value in values.items():
        raw_value = value.strip()
        if not raw_value:
            continue
        if key == "title":
            raw_value = protect_title_case(raw_value)
        if key in TEXT_FIELDS:
            escaped[key] = _escape_preserving_inserted_braces(raw_value)
        else:
            escaped[key] = escape_latex(raw_value)
    return escaped


def _ordered_fields(fields: dict[str, str]) -> list[tuple[str, str]]:
    preferred = [
        "author",
        "title",
        "journal",
        "booktitle",
        "publisher",
        "school",
        "institution",
        "series",
        "volume",
        "number",
        "pages",
        "year",
        "doi",
        "url",
        "eprint",
        "archivePrefix",
        "note",
    ]
    ordered: list[tuple[str, str]] = []
    for key in preferred:
        value = fields.get(key)
        if value:
            ordered.append((key, value))
    for key in sorted(fields):
        if key not in {name for name, _ in ordered} and fields[key]:
            ordered.append((key, fields[key]))
    return ordered


def _normalize_doi_url(doi: str) -> str:
    normalized = doi.strip()
    if not normalized:
        return ""
    if normalized.startswith("https://doi.org/") or normalized.startswith("http://doi.org/"):
        return normalized
    if normalized.startswith("10."):
        return f"https://doi.org/{normalized}"
    return normalized


def _escape_preserving_inserted_braces(text: str) -> str:
    result: list[str] = []
    depth = 0
    for char in text:
        if char == "{":
            depth += 1
            result.append(char)
            continue
        if char == "}":
            depth = max(depth - 1, 0)
            result.append(char)
            continue
        if depth > 0:
            result.append(LATEX_SPECIAL_CHARS.get(char, char) if char in {"\\", "%", "&", "$", "#", "_", "~", "^"} else char)
        else:
            result.append(escape_latex(char))
    return "".join(result)


def _has_balanced_braces(text: str) -> bool:
    depth = 0
    for char in text:
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def _contains_suspicious_unicode(metadata: dict[str, Any]) -> bool:
    for value in metadata.values():
        if isinstance(value, list):
            text = " ".join(str(item) for item in value)
        else:
            text = str(value)
        if any(ord(char) > 127 for char in text):
            return True
    return False


def _find_unescaped_special_chars(value: str) -> set[str]:
    specials: set[str] = set()
    for char in ("&", "%", "$", "#", "_"):
        if re.search(rf"(?<!\\){re.escape(char)}", value):
            specials.add(char)
    if re.search(r"(?<!\\)\^", value):
        specials.add("^")
    if re.search(r"(?<!\\)~", value):
        specials.add("~")
    return specials


def _smoke_tex_document() -> str:
    return "\n".join(
        [
            r"\documentclass{article}",
            r"\begin{document}",
            r"\nocite{*}",
            r"\bibliographystyle{plain}",
            r"\bibliography{references}",
            r"\end{document}",
            "",
        ]
    )

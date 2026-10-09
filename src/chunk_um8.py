#!/usr/bin/env python3
"""Chunk the written UM8 regulation while preserving legal structure and pages."""

import argparse
import hashlib
import json
import os
import re
import statistics
from typing import Any


DEFAULT_INPUT = "data/extracted/um8_chunk_source.txt"
DEFAULT_OUTPUT = "data/chunked/um8_chunks.json"
EXTRACTION_SUMMARY = "data/extracted/extraction_summary.json"
DEFAULT_ZONE = "UM 8"
DEFAULT_SOURCE = "PLUi de Bordeaux Métropole - Règlement écrit"
DEFAULT_VERSION = "version 30, publiée et en vigueur depuis le 12 mai 2026"
MAX_CHUNK_CHARS = 1500
OVERLAP_CHARS = 200

_PAGE_RE = re.compile(r"^## Page (\d+)\s*$")
_SECTION_RE = re.compile(r"^(\d+(?:\.\d+)*)\.\s+(.+?)\s*$")
_TOC_RE = re.compile(r"(?:\.{3,}|…)+\s*\d[\d\s]*\s*$")
_ZONE_HEADER_RE = re.compile(r"^Zone\s+UM\s+\d+$", re.IGNORECASE)
_REPEATED_HEADERS = {"règlement pièces écrites"}


def is_noise_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped or _PAGE_RE.fullmatch(stripped) or re.fullmatch(r"-{3,}", stripped):
        return True
    if _ZONE_HEADER_RE.fullmatch(stripped):
        return True
    if stripped.casefold() in _REPEATED_HEADERS:
        return True
    return bool(re.fullmatch(r"11e?\s+modification\s+du\s+PLU\s*\d*", stripped, re.IGNORECASE))


def is_toc_line(line: str) -> bool:
    """Detect rows ending in a printed page number and leaders."""
    return bool(_TOC_RE.search(line.strip()))


def clean_line(line: str) -> str:
    line = re.sub(r"\s+\.{2,}\s*\d[\d\s]*$", "", line)
    return line.strip()


def _is_wrapped_title_continuation(line: str) -> bool:
    """Recognize the common PDF layout where a long heading wraps to a lowercase line."""
    if not line or line.lstrip().startswith(("-", "•", "–")):
        return False
    first_letter = next((character for character in line if character.isalpha()), "")
    return bool(first_letter and first_letter.islower())


def parse_section_header(line: str) -> tuple[str, str] | None:
    match = _SECTION_RE.fullmatch(line.strip())
    if not match:
        return None
    return match.group(1), match.group(2).strip()


def iter_page_lines(raw_text: str):
    """Yield (PDF page number, line) pairs from the extraction's page markers."""
    current_page = None
    for line in raw_text.splitlines():
        match = _PAGE_RE.fullmatch(line.strip())
        if match:
            current_page = int(match.group(1))
        elif current_page is not None:
            yield current_page, line


def _is_body_heading(lines: list[tuple[int, str]], index: int) -> bool:
    page, line = lines[index]
    if is_toc_line(line):
        return False
    header = parse_section_header(line)
    if not header or header[0] != "1" or header[1].casefold() != "fonctions urbaines":
        return False

    # The table of contents also contains this title. In the actual article it
    # is followed by explanatory prose, while the TOC is followed by another
    # numbered row (sometimes wrapped onto the next line).
    for next_page, following in lines[index + 1:]:
        if next_page != page:
            return False
        if is_noise_line(following):
            continue
        if is_toc_line(following) or parse_section_header(following):
            return False
        return bool(clean_line(following))
    return False


def _body_start(lines: list[tuple[int, str]]) -> int | None:
    for index in range(len(lines)):
        if _is_body_heading(lines, index):
            return index
    return None


def extract_sections(raw_text: str) -> list[dict[str, Any]]:
    """Parse real article sections; discard all pages before the body heading."""
    lines = list(iter_page_lines(raw_text))
    start = _body_start(lines)
    if start is None:
        raise ValueError("Début du contenu introuvable : ‘1. Fonctions urbaines’ suivi de prose.")

    sections: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    content_lines: list[tuple[str, int]] = []

    def flush() -> None:
        if current is None:
            return
        current["content_lines"] = [
            {"text": text, "page": page} for text, page in content_lines
        ]
        current["content"] = "\n".join(text for text, _ in content_lines).strip()
        current["content_pages"] = sorted({page for _, page in content_lines})
        sections.append(current.copy())

    for page, line in lines[start:]:
        if is_noise_line(line) or is_toc_line(line):
            continue
        cleaned = clean_line(line)
        if not cleaned:
            continue

        header = parse_section_header(cleaned)
        if header:
            number, title = header
            if current is not None and number == current["number"]:
                # Repeated section title on a continuation page, not a new clause.
                continue
            flush()
            current = {"number": number, "title": title}
            content_lines = []
        elif current is not None:
            if not content_lines and _is_wrapped_title_continuation(cleaned):
                current["title"] += " " + cleaned
            else:
                content_lines.append((cleaned, page))

    flush()
    return sections


def build_page_map(raw_text: str) -> dict[str, list[int]]:
    """Map section numbers to pages that actually contain their extracted text."""
    return {section["number"]: section["content_pages"] for section in extract_sections(raw_text)}


def _split_spans(text: str, max_chars: int, overlap: int) -> list[tuple[str, int, int]]:
    if max_chars < 1:
        raise ValueError("max_chars doit être strictement positif")
    if overlap < 0 or overlap >= max_chars:
        raise ValueError("overlap doit être positif ou nul et inférieur à max_chars")
    if len(text) <= max_chars:
        return [(text, 0, len(text))] if text else []

    spans: list[tuple[str, int, int]] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        if end < len(text):
            newline = text.rfind("\n", start + 1, end + 1)
            if newline > start:
                end = newline
            else:
                whitespace = max(
                    text.rfind(character, start + 1, end + 1)
                    for character in (" ", "\t", "\r")
                )
                if whitespace > start:
                    end = whitespace
        part_start, part_end = start, end
        while part_start < part_end and text[part_start].isspace():
            part_start += 1
        while part_end > part_start and text[part_end - 1].isspace():
            part_end -= 1
        if part_start < part_end:
            spans.append((text[part_start:part_end], part_start, part_end))
        if end >= len(text):
            break
        next_start = max(start + 1, end - overlap)
        if (
            next_start < end
            and not text[next_start].isspace()
            and not text[next_start - 1].isspace()
        ):
            while next_start < end and not text[next_start].isspace():
                next_start += 1
        start = next_start
    return spans


def split_long_text(text: str, max_chars: int, overlap: int) -> list[str]:
    """Split at line boundaries where possible, retaining a character overlap."""
    return [part for part, _, _ in _split_spans(text, max_chars, overlap)]


def _char_pages(section: dict[str, Any], content: str, page_map: dict[str, list[int]]) -> list[int | None]:
    char_pages: list[int | None] = []
    content_lines = section.get("content_lines")
    if content_lines:
        for index, record in enumerate(content_lines):
            line = record["text"]
            char_pages.extend([record["page"]] * len(line))
            if index < len(content_lines) - 1:
                char_pages.append(record["page"])
    if len(char_pages) != len(content):
        fallback_pages = page_map.get(section["number"], section.get("content_pages", []))
        return [fallback_pages[0] if fallback_pages else None] * len(content)
    return char_pages


def make_chunk_id(
    source: str, version: str, zone: str, section: str, title: str, part_index: int, content: str
) -> str:
    payload = f"{source}|{version}|{zone}|{section}|{title}|{part_index}|{content}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def create_chunks(
    sections: list[dict[str, Any]],
    page_map: dict[str, list[int]],
    source: str,
    version: str,
    zone: str,
    max_chars: int = MAX_CHUNK_CHARS,
    overlap: int = OVERLAP_CHARS,
    page_extractors: dict[int, str] | None = None,
) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    for section in sections:
        number, title, content = section["number"], section["title"], section["content"]
        if not content.strip():
            continue
        char_pages = _char_pages(section, content, page_map)
        spans = _split_spans(content, max_chars, overlap)
        for part_index, (part, start, end) in enumerate(spans, start=1):
            pages = sorted({page for page in char_pages[start:end] if page is not None})
            if not pages:
                pages = sorted(set(page_map.get(number, [])))
            metadata = {
                "source": source,
                "version": version,
                "zone": zone,
                "pages": pages,
                "page_basis": "numéros de pages PDF, à partir de 1",
                "section_title": title,
            }
            if page_extractors:
                metadata["extraction_methods"] = sorted({
                    page_extractors[page] for page in pages if page in page_extractors
                })
            if len(spans) > 1:
                metadata["part"] = f"{part_index}/{len(spans)}"
            chunks.append({
                "id": make_chunk_id(source, version, zone, number, title, part_index, part),
                "type": "section",
                "section_number": number,
                "title": title,
                "content": part,
                "metadata": metadata,
            })
    return chunks


def save_chunks(
    chunks: list[dict[str, Any]], path: str, max_chars: int, overlap: int
) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    output = {
        "chunks": chunks,
        "metadata": {
            "total_chunks": len(chunks),
            "chunking_method": "hierarchical_sections",
            "max_chunk_chars": max_chars,
            "overlap_chars": overlap,
            "description": "Chunks réglementaires avec section et pages PDF réellement couvertes.",
        },
    }
    with open(path, "w", encoding="utf-8") as file:
        json.dump(output, file, indent=2, ensure_ascii=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Chunking réglementaire du chapitre UM8")
    parser.add_argument("--input", default=DEFAULT_INPUT, help="Fichier texte extrait")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Fichier JSON de sortie")
    parser.add_argument("--zone", default=DEFAULT_ZONE, help="Nom de la zone")
    parser.add_argument("--max-chars", type=int, default=MAX_CHUNK_CHARS)
    parser.add_argument("--overlap-chars", type=int, default=OVERLAP_CHARS)
    args = parser.parse_args()
    if not os.path.exists(args.input):
        parser.error(f"fichier introuvable : {args.input}")
    if args.max_chars < 1 or args.overlap_chars < 0 or args.overlap_chars >= args.max_chars:
        parser.error("--max-chars doit être positif et --overlap-chars compris entre 0 et max_chars - 1")

    with open(args.input, "r", encoding="utf-8") as file:
        raw_text = file.read()
    page_extractors: dict[int, str] = {}
    if os.path.exists(EXTRACTION_SUMMARY):
        with open(EXTRACTION_SUMMARY, "r", encoding="utf-8") as file:
            summary = json.load(file)
        page_extractors = {
            int(page): method for page, method in summary.get("chunk_source_extractors", {}).items()
        }
    try:
        sections = extract_sections(raw_text)
    except ValueError as error:
        parser.error(str(error))
    page_map = {section["number"]: section["content_pages"] for section in sections}
    sections_with_content = [section for section in sections if section["content"].strip()]
    chunks = create_chunks(
        sections_with_content, page_map, DEFAULT_SOURCE, DEFAULT_VERSION, args.zone,
        args.max_chars, args.overlap_chars, page_extractors,
    )
    save_chunks(chunks, args.output, args.max_chars, args.overlap_chars)

    lengths = [len(chunk["content"]) for chunk in chunks]
    print(f"Sections : {len(sections)} ({len(sections) - len(sections_with_content)} sans contenu ignorées)")
    print(f"Chunks : {len(chunks)}")
    if lengths:
        print(f"Taille : min={min(lengths)}, médiane={statistics.median(lengths):.1f}, max={max(lengths)} caractères")
    print(f"Sortie : {args.output}")


if __name__ == "__main__":
    main()

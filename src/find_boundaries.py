#!/usr/bin/env python3
"""Find the body-page range for a zone using exact page headers."""

import argparse
import re

import pypdf


DEFAULT_PDF = "data/243300316_reglement_20260505.pdf"
_TOC_RE = re.compile(r"(?:\.{3,}|…)+\s*\d[\d\s]*\s*$")
_NUMBERED_HEADING_RE = re.compile(r"^\d+(?:\.\d+)*\.\s+.+$")


def _has_exact_line(text: str, expected: str) -> bool:
    return any(line.strip().casefold() == expected.strip().casefold() for line in text.splitlines())


def _has_body_start(text: str) -> bool:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.strip().casefold() != "1. fonctions urbaines":
            continue
        if _TOC_RE.search(line.strip()):
            continue
        for following in lines[index + 1:]:
            candidate = following.strip()
            if not candidate or candidate.casefold() in {"zone um 8", "règlement pièces écrites"}:
                continue
            if _TOC_RE.search(candidate) or _NUMBERED_HEADING_RE.fullmatch(candidate):
                break
            return True
        break
    return False


def find_zone_boundaries(pdf_path: str, target_zone: str, next_zone: str) -> tuple[int, int]:
    """Return 1-based first/last body pages carrying exact zone headers.

    The table of contents is deliberately ignored: the start is accepted only
    when the exact article heading is followed by prose on the same page.
    """
    reader = pypdf.PdfReader(pdf_path)
    start_page: int | None = None
    last_target_page: int | None = None

    for index, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        page_num = index + 1
        has_target = _has_exact_line(text, target_zone)
        if start_page is None and has_target and _has_body_start(text):
            start_page = page_num
        if start_page is None:
            continue
        if _has_exact_line(text, next_zone):
            break
        if has_target:
            last_target_page = page_num

    if start_page is None:
        raise ValueError(f"Début du corps de {target_zone!r} introuvable.")
    if last_target_page is None:
        raise ValueError(f"Aucune page de contenu avec l'en-tête exact {target_zone!r}.")
    return start_page, last_target_page


def main() -> None:
    parser = argparse.ArgumentParser(description="Trouve les pages du corps d'une zone réglementaire.")
    parser.add_argument("--pdf", default=DEFAULT_PDF, help="Chemin du PDF")
    parser.add_argument("--zone", default="Zone UM 8", help="En-tête exact de la zone")
    parser.add_argument("--next-zone", default="Zone UM 9", help="En-tête exact de la zone suivante")
    args = parser.parse_args()
    try:
        start_page, end_page = find_zone_boundaries(args.pdf, args.zone, args.next_zone)
    except (FileNotFoundError, ValueError) as error:
        parser.error(str(error))
    print(f"{args.zone} : pages PDF {start_page}-{end_page} ({end_page - start_page + 1} pages)")


if __name__ == "__main__":
    main()

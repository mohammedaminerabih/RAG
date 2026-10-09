#!/usr/bin/env python3
"""
Extraction du chapitre UM8 du règlement PLUi de Bordeaux Métropole.

Compare deux extracteurs PDF (pypdf et pdfplumber) et génère un rapport
de contrôle qualité page par page.
"""

import argparse
from collections import Counter
import json
import os
import re
import sys
import unicodedata
from datetime import datetime

import pypdf
import pdfplumber
from find_boundaries import find_zone_boundaries


# --- Configuration par défaut --------------------------------------------------------

DEFAULT_PDF = "data/243300316_reglement_20260505.pdf"
DEFAULT_OUTPUT_DIR = "data/extracted"
SIMILARITY_THRESHOLD = 0.98
DEFAULT_CHUNK_EXTRACTOR = "pdfplumber"
# Page 322 also contains a reviewed table, but neither extractor preserves its
# cell relationships reliably, so table-dependent questions remain excluded.
# Page 324 was visually reviewed. On pages 327-328, pdfplumber detaches H_F/H_T
# subscripts; pypdf preserves their reading order better.
PAGE_EXTRACTOR_OVERRIDES = {324: "pypdf", 327: "pypdf", 328: "pypdf"}


def _validate_page_range(start_page: int, end_page: int, total_pages: int) -> None:
    """Refuser une plage invalide au lieu de tronquer silencieusement l'extraction."""
    if start_page < 1 or end_page < start_page:
        raise ValueError(f"Plage de pages invalide : {start_page}-{end_page}")
    if end_page > total_pages:
        raise ValueError(
            f"La page de fin {end_page} dépasse le PDF ({total_pages} pages)"
        )


def resolve_page_range(
    pdf_path: str, start_page: int | None, end_page: int | None
) -> tuple[int, int]:
    """Find UM8 boundaries by default; require both explicit bounds if overridden."""
    if start_page is None and end_page is None:
        return find_zone_boundaries(pdf_path, "Zone UM 8", "Zone UM 9")
    if start_page is None or end_page is None:
        raise ValueError("Fournir --start et --end ensemble, ou aucun des deux.")
    return start_page, end_page


# --- Fonctions d'extraction ----------------------------------------------------------

def extract_with_pypdf(pdf_path: str, start_page: int, end_page: int) -> dict[int, str]:
    """Extraire le texte page par page avec PyPDF."""
    text_by_page = {}
    try:
        with open(pdf_path, "rb") as f:
            reader = pypdf.PdfReader(f)
            _validate_page_range(start_page, end_page, len(reader.pages))
            for page_num in range(start_page - 1, end_page):
                text_by_page[page_num + 1] = reader.pages[page_num].extract_text() or ""
    except FileNotFoundError:
        print(f"ERREUR : fichier introuvable — {pdf_path}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERREUR PyPDF : {e}", file=sys.stderr)
        sys.exit(1)
    return text_by_page


def extract_with_pdfplumber(pdf_path: str, start_page: int, end_page: int) -> dict[int, str]:
    """Extraire le texte page par page avec pdfplumber."""
    text_by_page = {}
    try:
        with pdfplumber.open(pdf_path) as pdf:
            _validate_page_range(start_page, end_page, len(pdf.pages))
            for page_num in range(start_page - 1, end_page):
                text_by_page[page_num + 1] = pdf.pages[page_num].extract_text() or ""
    except FileNotFoundError:
        print(f"ERREUR : fichier introuvable — {pdf_path}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERREUR pdfplumber : {e}", file=sys.stderr)
        sys.exit(1)
    return text_by_page


# --- Comparaison et sauvegarde -------------------------------------------------------

def normalize_height_subscripts(text: str) -> str:
    """Join H_F/H_T markers that PDF extraction may separate with whitespace."""
    # PDF text layers sometimes expose typographic subscripts as separated words.
    return re.sub(r"\bH\s+([FT])\b", r"H\1", text, flags=re.IGNORECASE)


def normalize_extracted_markers(text: str) -> str:
    """Repair known PDF font-map failures for list bullets and height subscripts."""
    text = normalize_height_subscripts(text)
    return re.sub(r"(?m)^\ufffd{2}(?=\s)", "•", text)


def normalize_extracted_text(text: str) -> str:
    """Normaliser les différences de mise en page avant de comparer les extracteurs."""
    text = unicodedata.normalize("NFC", text).replace("\u00ad", "")
    text = re.sub(r"(?<=\w)-\s*\n\s*(?=\w)", "", text)
    text = normalize_height_subscripts(text)
    return re.sub(r"\s+", " ", text).strip()


def word_f1_similarity(text_a: str, text_b: str) -> float:
    """Compare extracted word multisets, without penalizing layout reordering."""
    tokens_a = re.findall(r"\w+", normalize_extracted_text(text_a).casefold(), flags=re.UNICODE)
    tokens_b = re.findall(r"\w+", normalize_extracted_text(text_b).casefold(), flags=re.UNICODE)
    if not tokens_a and not tokens_b:
        return 1.0
    if not tokens_a or not tokens_b:
        return 0.0
    overlap = sum((Counter(tokens_a) & Counter(tokens_b)).values())
    return 2 * overlap / (len(tokens_a) + len(tokens_b))


def compare_extractions(pypdf_text: dict, pdfplumber_text: dict) -> dict:
    """Comparer les textes bruts et le recouvrement lexical après normalisation."""
    comparison = {}
    for page_num in sorted(set(pypdf_text) | set(pdfplumber_text)):
        a = pypdf_text.get(page_num, "")
        b = pdfplumber_text.get(page_num, "")
        normalized_a = normalize_extracted_text(a)
        normalized_b = normalize_extracted_text(b)
        word_f1 = word_f1_similarity(a, b)
        comparison[str(page_num)] = {
            "pypdf_length": len(a),
            "pdfplumber_length": len(b),
            "length_diff": abs(len(a) - len(b)),
            "content_equal": a == b,
            "normalized_equal": normalized_a == normalized_b,
            "word_f1_similarity": round(word_f1, 4),
            # Keep the generic key used by the CLI and previous artifact readers.
            "normalized_similarity": round(word_f1, 4),
        }
    return comparison


def select_chunk_source(
    pypdf_text: dict[int, str],
    pdfplumber_text: dict[int, str],
    overrides: dict[int, str] | None = None,
) -> tuple[dict[int, str], dict[int, str]]:
    """Choose one extractor per page and return text plus an auditable method map."""
    overrides = overrides or {}
    available_pages = set(pypdf_text) | set(pdfplumber_text)
    unknown_pages = sorted(set(overrides) - available_pages)
    if unknown_pages:
        raise ValueError(f"Texte manquant pour les pages configurées : {unknown_pages}")
    selected: dict[int, str] = {}
    methods: dict[int, str] = {}
    for page_num in sorted(set(pypdf_text) | set(pdfplumber_text)):
        method = overrides.get(page_num, DEFAULT_CHUNK_EXTRACTOR)
        candidates = {"pypdf": pypdf_text, "pdfplumber": pdfplumber_text}
        if method not in candidates:
            raise ValueError(f"Extracteur inconnu pour la page {page_num} : {method}")
        if page_num not in candidates[method]:
            raise ValueError(f"Texte manquant pour la page {page_num} via {method}")
        selected[page_num] = normalize_extracted_markers(candidates[method][page_num])
        methods[page_num] = method
    return selected, methods


def save_text(text_by_page: dict, path: str, method: str) -> None:
    """Écrire le texte extrait dans un fichier avec marqueurs de page."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# Texte extrait avec {method}\n\n")
        for page_num in sorted(text_by_page):
            f.write(f"## Page {page_num}\n\n")
            f.write(text_by_page[page_num])
            f.write("\n\n---\n\n")


# --- Validation de la frontière de zone ----------------------------------------------

def validate_zone_boundary(text_by_page: dict, zone_label: str = "Zone UM 8") -> list[int]:
    """
    Vérifier que chaque page non vide porte une ligne d'en-tête exacte pour la zone.
    Une simple mention de la zone dans le corps du texte ne suffit pas.
    """
    expected = re.sub(r"\s+", " ", zone_label.strip()).casefold()
    wrong_zone_pages: list[int] = []
    for page_num, text in text_by_page.items():
        headers = [
            re.sub(r"\s+", " ", line.strip()).casefold()
            for line in text.splitlines()
            if re.fullmatch(r"Zone\s+UM\s+\d+", line.strip(), flags=re.IGNORECASE)
        ]
        if text.strip() and expected not in headers:
            wrong_zone_pages.append(page_num)
    return wrong_zone_pages


# --- Point d'entrée ------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Extraction du chapitre UM8 du PLUi")
    parser.add_argument("--pdf", default=DEFAULT_PDF, help="Chemin du PDF source")
    parser.add_argument("--start", type=int, help="Page de début (incluse); à fournir avec --end")
    parser.add_argument("--end", type=int, help="Page de fin (incluse); à fournir avec --start")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="Dossier de sortie")
    args = parser.parse_args()

    if not os.path.exists(args.pdf):
        print(f"ERREUR : fichier PDF introuvable — {args.pdf}", file=sys.stderr)
        sys.exit(1)

    try:
        start_page, end_page = resolve_page_range(args.pdf, args.start, args.end)
    except (FileNotFoundError, ValueError) as error:
        parser.error(str(error))

    print(f"Extraction : {args.pdf}  (pages {start_page}-{end_page})")

    # Extraction
    print("  - PyPDF ...")
    pypdf_text = extract_with_pypdf(args.pdf, start_page, end_page)
    print("  - pdfplumber ...")
    pdfplumber_text = extract_with_pdfplumber(args.pdf, start_page, end_page)

    # Validation stricte de la plage : ne pas produire silencieusement un corpus mixte.
    wrong_pages = validate_zone_boundary(pdfplumber_text)
    if wrong_pages:
        raise SystemExit(
            f"En-tête UM8 absent ou incorrect sur les pages non vides : {wrong_pages}. "
            "Aucun fichier de sortie n'a été écrit."
        )

    # Comparaison
    comparison = compare_extractions(pypdf_text, pdfplumber_text)
    active_overrides = {
        page: method for page, method in PAGE_EXTRACTOR_OVERRIDES.items()
        if page in pypdf_text or page in pdfplumber_text
    }
    chunk_text, chunk_extractors = select_chunk_source(
        pypdf_text, pdfplumber_text, active_overrides
    )
    pages_with_raw_diff = sum(1 for d in comparison.values() if not d["content_equal"])
    pages_below_threshold = [
        int(page_num)
        for page_num, diff in comparison.items()
        if diff["normalized_similarity"] < SIMILARITY_THRESHOLD
    ]

    # Sauvegarde
    os.makedirs(args.output_dir, exist_ok=True)
    save_text(pypdf_text, f"{args.output_dir}/um8_pypdf.txt", "PyPDF")
    save_text(pdfplumber_text, f"{args.output_dir}/um8_pdfplumber.txt", "pdfplumber")
    save_text(
        chunk_text,
        f"{args.output_dir}/um8_chunk_source.txt",
        "sélection contrôlée (pdfplumber par défaut; pypdf pages 324, 327 et 328)",
    )

    with open(f"{args.output_dir}/comparison.json", "w", encoding="utf-8") as f:
        json.dump(comparison, f, indent=2, ensure_ascii=False)

    summary = {
        "pdf_source": args.pdf,
        "extraction_range": f"{start_page}-{end_page}",
        "total_pages": len(comparison),
        "pages_with_raw_text_differences": pages_with_raw_diff,
        "similarity_threshold": SIMILARITY_THRESHOLD,
        "similarity_method": "F1 des multiensembles de mots après normalisation; l'ordre de mise en page est ignoré",
        "pages_below_similarity_threshold": pages_below_threshold,
        "chunk_source_file": "um8_chunk_source.txt",
        "chunk_source_extractors": {str(page): method for page, method in chunk_extractors.items()},
        "manual_review_required": pages_below_threshold,
        "extraction_date": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    with open(f"{args.output_dir}/extraction_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    # Rapport
    print(f"\n{'='*50}")
    print(f"  Pages extraites : {len(comparison)}")
    print(f"  Pages où les sorties brutes diffèrent (mise en page incluse) : {pages_with_raw_diff}")
    print(
        f"  Pages à vérifier (F1 lexical normalisé < {SIMILARITY_THRESHOLD:.0%}) : "
        f"{len(pages_below_threshold)} {pages_below_threshold}"
    )
    print(f"  Resultats : {args.output_dir}/")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()

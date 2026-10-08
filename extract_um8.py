#!/usr/bin/env python3
"""
Extraction du chapitre UM8 du règlement PLUi de Bordeaux Métropole.

Compare deux extracteurs PDF (pypdf et pdfplumber) et génère un rapport
de contrôle qualité page par page.
"""

import argparse
import json
import os
import sys
from datetime import datetime

import pypdf
import pdfplumber


# --- Configuration par défaut --------------------------------------------------------

DEFAULT_PDF = "data/243300316_reglement_20260505.pdf"
DEFAULT_START_PAGE = 300
DEFAULT_END_PAGE = 342  # UM9 commence page 343 — on s'arrête avant
DEFAULT_OUTPUT_DIR = "extracted"


# --- Fonctions d'extraction ----------------------------------------------------------

def extract_with_pypdf(pdf_path: str, start_page: int, end_page: int) -> dict[int, str]:
    """Extraire le texte page par page avec PyPDF."""
    text_by_page = {}
    try:
        with open(pdf_path, "rb") as f:
            reader = pypdf.PdfReader(f)
            for page_num in range(start_page - 1, end_page):
                if page_num < len(reader.pages):
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
            for page_num in range(start_page - 1, end_page):
                if page_num < len(pdf.pages):
                    text_by_page[page_num + 1] = pdf.pages[page_num].extract_text() or ""
    except FileNotFoundError:
        print(f"ERREUR : fichier introuvable — {pdf_path}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERREUR pdfplumber : {e}", file=sys.stderr)
        sys.exit(1)
    return text_by_page


# --- Comparaison et sauvegarde -------------------------------------------------------

def compare_extractions(pypdf_text: dict, pdfplumber_text: dict) -> dict:
    """Comparer les deux extractions page par page."""
    comparison = {}
    for page_num in sorted(set(pypdf_text) | set(pdfplumber_text)):
        a = pypdf_text.get(page_num, "")
        b = pdfplumber_text.get(page_num, "")
        comparison[str(page_num)] = {
            "pypdf_length": len(a),
            "pdfplumber_length": len(b),
            "length_diff": abs(len(a) - len(b)),
            "content_equal": a == b,
        }
    return comparison


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
    Vérifier que chaque page contient bien le header de la zone attendue.
    Retourne la liste des pages contenant un header de zone *différent*.
    """
    wrong_zone_pages = []
    for page_num, text in text_by_page.items():
        # Chercher n'importe quel header "Zone UM X"
        if "Zone UM" in text and zone_label not in text:
            wrong_zone_pages.append(page_num)
    return wrong_zone_pages


# --- Point d'entrée ------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Extraction du chapitre UM8 du PLUi")
    parser.add_argument("--pdf", default=DEFAULT_PDF, help="Chemin du PDF source")
    parser.add_argument("--start", type=int, default=DEFAULT_START_PAGE, help="Page de début (incluse)")
    parser.add_argument("--end", type=int, default=DEFAULT_END_PAGE, help="Page de fin (incluse)")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="Dossier de sortie")
    args = parser.parse_args()

    if not os.path.exists(args.pdf):
        print(f"ERREUR : fichier PDF introuvable — {args.pdf}", file=sys.stderr)
        sys.exit(1)

    print(f"Extraction : {args.pdf}  (pages {args.start}-{args.end})")

    # Extraction
    print("  - PyPDF ...")
    pypdf_text = extract_with_pypdf(args.pdf, args.start, args.end)
    print("  - pdfplumber ...")
    pdfplumber_text = extract_with_pdfplumber(args.pdf, args.start, args.end)

    # Validation de zone
    wrong_pages = validate_zone_boundary(pdfplumber_text)
    if wrong_pages:
        print(f"  [!] Pages avec zone incorrecte (hors UM8) : {wrong_pages}")
        print(f"     -> ces pages seront exclues du fichier de sortie")
        for p in wrong_pages:
            pypdf_text.pop(p, None)
            pdfplumber_text.pop(p, None)

    # Comparaison
    comparison = compare_extractions(pypdf_text, pdfplumber_text)
    pages_with_diff = sum(1 for d in comparison.values() if d["length_diff"] > 10)

    # Sauvegarde
    os.makedirs(args.output_dir, exist_ok=True)
    save_text(pypdf_text, f"{args.output_dir}/um8_pypdf.txt", "PyPDF")
    save_text(pdfplumber_text, f"{args.output_dir}/um8_pdfplumber.txt", "pdfplumber")

    with open(f"{args.output_dir}/comparison.json", "w", encoding="utf-8") as f:
        json.dump(comparison, f, indent=2, ensure_ascii=False)

    summary = {
        "pdf_source": args.pdf,
        "extraction_range": f"{args.start}-{args.end}",
        "total_pages": len(comparison),
        "pages_with_significant_diff": pages_with_diff,
        "excluded_wrong_zone_pages": wrong_pages,
        "extraction_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    with open(f"{args.output_dir}/extraction_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    # Rapport
    print(f"\n{'='*50}")
    print(f"  Pages extraites : {len(comparison)}")
    print(f"  Différences significatives (>10 chars) : {pages_with_diff}")
    print(f"  Pages exclues (zone incorrecte) : {len(wrong_pages)}")
    print(f"  Resultats : {args.output_dir}/")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
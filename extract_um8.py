#!/usr/bin/env python3
"""
Script pour extraire le chapitre UM8 du règlement PLUi de Bordeaux Métropole
et réaliser un contrôle qualité de l'extraction.
"""

import pypdf
import pdfplumber
import pandas as pd
import os
import json
from pathlib import Path

def extract_with_pypdf(pdf_path, start_page, end_page):
    """Extraire du texte avec PyPDF"""
    text_by_page = {}
    with open(pdf_path, 'rb') as file:
        reader = pypdf.PdfReader(file)
        for page_num in range(start_page-1, end_page):  # pages are 0-indexed
            if page_num < len(reader.pages):
                page = reader.pages[page_num]
                text = page.extract_text()
                text_by_page[page_num + 1] = text  # store with 1-indexed page numbers
    return text_by_page

def extract_with_pdfplumber(pdf_path, start_page, end_page):
    """Extraire du texte avec pdfplumber"""
    text_by_page = {}
    with pdfplumber.open(pdf_path) as pdf:
        for page_num in range(start_page-1, end_page):  # pages are 0-indexed
            if page_num < len(pdf.pages):
                page = pdf.pages[page_num]
                text = page.extract_text()
                text_by_page[page_num + 1] = text  # store with 1-indexed page numbers
    return text_by_page

def compare_extractions(pypdf_text, pdfplumber_text):
    """Comparer les extractions des deux méthodes"""
    comparison = {}
    all_pages = set(pypdf_text.keys()) | set(pdfplumber_text.keys())

    for page_num in all_pages:
        pypdf_content = pypdf_text.get(page_num, "")
        pdfplumber_content = pdfplumber_text.get(page_num, "")

        # Calculer quelques métriques de comparaison
        comparison[page_num] = {
            'pypdf_length': len(pypdf_content),
            'pdfplumber_length': len(pdfplumber_content),
            'length_diff': abs(len(pypdf_content) - len(pdfplumber_content)),
            'pypdf_has_content': bool(pypdf_content.strip()),
            'pdfplumber_has_content': bool(pdfplumber_content.strip()),
            'content_equal': pypdf_content == pdfplumber_content
        }

    return comparison

def save_extracted_text(text_by_page, output_path, method_name):
    """Sauvegarder le texte extrait"""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"# Texte extrait avec {method_name}\n\n")
        for page_num in sorted(text_by_page.keys()):
            f.write(f"## Page {page_num}\n\n")
            f.write(text_by_page[page_num])
            f.write("\n\n---\n\n")

def main():
    pdf_path = "data/243300316_reglement_20260505.pdf"

    # D'après le journal.md, UM8 occupe environ les pages PDF 301-340
    # On va faire une extraction légèrement plus large pour être sûr
    start_page = 300  # un peu avant pour s'assurer de ne pas manquer le début
    end_page = 350    # un peu après pour s'assurer de ne pas manquer la fin

    print(f"Extraction du PDF: {pdf_path}")
    print(f"Pages ciblées: {start_page} à {end_page}")

    # Extraire avec les deux méthodes
    print("\nExtraction avec PyPDF...")
    pypdf_text = extract_with_pypdf(pdf_path, start_page, end_page)

    print("Extraction avec pdfplumber...")
    pdfplumber_text = extract_with_pdfplumber(pdf_path, start_page, end_page)

    # Comparer les extractions
    print("\nComparaison des extractions...")
    comparison = compare_extractions(pypdf_text, pdfplumber_text)

    # Sauvegarder les résultats
    output_dir = "extracted"
    os.makedirs(output_dir, exist_ok=True)

    # Sauvegarder les textes extraits
    save_extracted_text(pypdf_text, f"{output_dir}/um8_pypdf.txt", "PyPDF")
    save_extracted_text(pdfplumber_text, f"{output_dir}/um8_pdfplumber.txt", "pdfplumber")

    # Sauvegarder la comparaison en JSON
    with open(f"{output_dir}/comparison.json", 'w', encoding='utf-8') as f:
        json.dump(comparison, f, indent=2, ensure_ascii=False)

    # Créer un rapport de comparaison simplifié
    total_pages = len(comparison)
    pages_with_diff = sum(1 for data in comparison.values() if data['length_diff'] > 10)
    pages_equal_content = sum(1 for data in comparison.values() if data['content_equal'])

    print(f"\n=== RAPPORT D'EXTRACTION ===")
    print(f"Pages traitées: {total_pages}")
    print(f"Pages avec différence significative (>10 caractères): {pages_with_diff}")
    print(f"Pages avec contenu identique: {pages_equal_content}")

    # Sauvegarder le résumé
    summary = {
        'pdf_source': pdf_path,
        'extraction_range': f'{start_page}-{end_page}',
        'total_pages': total_pages,
        'pages_with_significant_diff': pages_with_diff,
        'pages_identical_content': pages_equal_content,
        'extraction_date': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    with open(f"{output_dir}/extraction_summary.json", 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"\nRésultats sauvegardés dans le dossier: {output_dir}")
    print("- Texte extrait (PyPDF): um8_pypdf.txt")
    print("- Texte extrait (pdfplumber): um8_pdfplumber.txt")
    print("- Comparaison détaillée: comparison.json")
    print("- Résumé: extraction_summary.json")

if __name__ == "__main__":
    main()
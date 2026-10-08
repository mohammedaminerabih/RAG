#!/usr/bin/env python3
"""Tests unitaires pour le pipeline de chunking UM8."""

import json
import os
import sys
import tempfile

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chunk_um8 import (
    is_noise_line,
    is_toc_line,
    clean_line,
    parse_section_header,
    extract_sections,
    split_long_text,
    create_chunks,
    build_page_map,
)


# =============================================================================
# Fixtures
# =============================================================================

SAMPLE_UM8_TEXT = """# Texte extrait avec pdfplumber

## Page 301

Zone UM 8
Règlement pièces écrites
1. Fonctions urbaines ...........................................................................................................................................................................5
1.1. Destination des constructions ..............................................................................................................................................5
1.2. Occupations et utilisations du sol interdites .....................................................................................................................7
11e modification du PLU 3

---

## Page 303

Zone UM 8
Règlement pièces écrites
1. Fonctions urbaines
Le présent chapitre permet de connaître les occupations et utilisations autorisées.
1.1. Destination des constructions
Les destinations des constructions sont définies en application du Code de l'urbanisme.
Ces définitions sont communes à l'ensemble des zones.
Pour connaître les destinations autorisées sur la zone, il faut se référer aux chapitres suivants.
Important : Les destinations qui ne sont ni interdites ni soumises à conditions sont autorisées.
11e modification du PLU 5

---

## Page 304

Zone UM 8
Règlement pièces écrites
1.2. Occupations et utilisations du sol interdites
Sont interdites les occupations et utilisations du sol suivantes :
- Les constructions à destination d'industrie.
- Les constructions à destination d'exploitation agricole.
- Les constructions à destination d'exploitation forestière.
11e modification du PLU 6

---

## Page 305

Zone UM 8
Règlement pièces écrites
1.2. Occupations et utilisations du sol interdites
- Les dépôts de véhicules à ciel ouvert.
- Les terrains de camping et de caravanage.
"""


# =============================================================================
# Tests : is_noise_line
# =============================================================================

def test_noise_page_header():
    assert is_noise_line("## Page 301")

def test_noise_separator():
    assert is_noise_line("---")
    assert is_noise_line("  -----  ")

def test_noise_zone_header():
    assert is_noise_line("Zone UM 8")

def test_noise_reglement_header():
    assert is_noise_line("Règlement pièces écrites")

def test_noise_plu_modification():
    assert is_noise_line("11e modification du PLU 3")
    assert is_noise_line("11 modification du PLU")

def test_noise_empty():
    assert is_noise_line("")
    assert is_noise_line("   ")

def test_not_noise_content():
    assert not is_noise_line("Les constructions à destination d'industrie.")
    assert not is_noise_line("1.1. Destination des constructions")


# =============================================================================
# Tests : is_toc_line
# =============================================================================

def test_toc_with_dots():
    assert is_toc_line("1. Fonctions urbaines ...............................5")
    assert is_toc_line("1.1. Destination des constructions ..............5")

def test_toc_with_ellipsis():
    assert is_toc_line("1.2. Occupations interdites …7")

def test_not_toc_content():
    assert not is_toc_line("1.1. Destination des constructions")
    assert not is_toc_line("Les constructions sont définies ci-après.")


# =============================================================================
# Tests : parse_section_header
# =============================================================================

def test_header_simple():
    result = parse_section_header("1. Fonctions urbaines")
    assert result == ("1", "Fonctions urbaines")

def test_header_nested():
    result = parse_section_header("1.3.2. Conditions particulières")
    assert result == ("1.3.2", "Conditions particulières")

def test_header_not_a_header():
    assert parse_section_header("Les constructions sont définies.") is None
    assert parse_section_header("") is None
    assert parse_section_header("- Les dépôts de véhicules") is None


# =============================================================================
# Tests : extract_sections
# =============================================================================

def test_extract_sections_filters_toc():
    """Les lignes de TdM ne doivent pas créer de sections."""
    sections = extract_sections(SAMPLE_UM8_TEXT)
    # Vérifier qu'aucune section n'a un contenu vide issu de la TdM
    for s in sections:
        if s["content"]:
            assert "....." not in s["content"], f"TdM leak in section {s['number']}"

def test_extract_sections_no_empty():
    """Les sections sans contenu sont quand même retournées mais avec content vide."""
    sections = extract_sections(SAMPLE_UM8_TEXT)
    # On doit avoir des sections avec du contenu
    non_empty = [s for s in sections if s["content"].strip()]
    assert len(non_empty) >= 2  # au moins 1.1 et 1.2

def test_extract_sections_no_duplicates():
    """La section 1.2 apparaît sur 2 pages — elle ne doit pas être dupliquée."""
    sections = extract_sections(SAMPLE_UM8_TEXT)
    numbers = [s["number"] for s in sections]
    # Chaque numéro de section doit être unique
    assert len(numbers) == len(set(numbers)), f"Sections dupliquées: {numbers}"

def test_extract_sections_accumulates_across_pages():
    """Le contenu de la section 1.2 (pages 304-305) doit être accumulé."""
    sections = extract_sections(SAMPLE_UM8_TEXT)
    sec_12 = next((s for s in sections if s["number"] == "1.2"), None)
    assert sec_12 is not None
    assert "industrie" in sec_12["content"]
    assert "camping" in sec_12["content"]


# =============================================================================
# Tests : split_long_text
# =============================================================================

def test_split_short_text():
    """Un texte court ne doit pas être découpé."""
    result = split_long_text("Court texte", 1500, 200)
    assert len(result) == 1
    assert result[0] == "Court texte"

def test_split_long_text():
    """Un texte long doit être découpé en plusieurs morceaux."""
    long_text = "\n".join(f"Ligne numéro {i} du texte réglementaire." for i in range(100))
    result = split_long_text(long_text, 500, 100)
    assert len(result) > 1
    # Chaque morceau doit faire <= max_chars (ou un peu plus si pas de \n)
    for part in result:
        assert len(part) <= 600  # marge pour le cas sans \n

def test_split_preserves_content():
    """Tout le contenu original doit être présent dans au moins un chunk."""
    lines = [f"Ligne {i}" for i in range(50)]
    text = "\n".join(lines)
    parts = split_long_text(text, 200, 50)
    for line in lines:
        assert any(line in part for part in parts), f"Ligne perdue: {line}"


# =============================================================================
# Tests : create_chunks (intégration)
# =============================================================================

def test_create_chunks_no_empty():
    """Aucun chunk vide ne doit être produit."""
    sections = extract_sections(SAMPLE_UM8_TEXT)
    sections = [s for s in sections if s["content"].strip()]
    page_map = build_page_map(SAMPLE_UM8_TEXT)
    chunks = create_chunks(sections, page_map, "test", "v1", "UM 8")
    assert len(chunks) > 0
    for c in chunks:
        assert c["content"].strip(), f"Chunk vide: {c['id']}"

def test_create_chunks_metadata():
    """Chaque chunk doit avoir les métadonnées requises."""
    sections = extract_sections(SAMPLE_UM8_TEXT)
    sections = [s for s in sections if s["content"].strip()]
    page_map = build_page_map(SAMPLE_UM8_TEXT)
    chunks = create_chunks(sections, page_map, "test-source", "v1", "UM 8")
    for c in chunks:
        assert "id" in c
        assert "section_number" in c
        assert "title" in c
        assert "content" in c
        meta = c["metadata"]
        assert meta["source"] == "test-source"
        assert meta["zone"] == "UM 8"


# =============================================================================
# Tests : build_page_map
# =============================================================================

def test_page_map():
    """Les sections doivent être associées aux bonnes pages."""
    page_map = build_page_map(SAMPLE_UM8_TEXT)
    assert "1.1" in page_map
    assert 303 in page_map["1.1"]
    assert "1.2" in page_map
    assert 304 in page_map["1.2"] or 305 in page_map["1.2"]


# =============================================================================
# Run
# =============================================================================

if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])

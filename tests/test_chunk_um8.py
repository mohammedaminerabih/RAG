#!/usr/bin/env python3
"""Tests unitaires pour le pipeline de chunking UM8."""

import json
import os
import sys

# Ajouter le répertoire src au path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

from chunk_um8 import (
    is_noise_line,
    is_toc_line,
    clean_line,
    parse_section_header,
    extract_sections,
    split_long_text,
    create_chunks,
    build_page_map,
    save_chunks,
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
    # Each chunk must respect the configured character limit.
    for part in result:
        assert len(part) <= 500

def test_split_preserves_content():
    """Tout le contenu original doit être présent dans au moins un chunk."""
    lines = [f"Ligne {i}" for i in range(50)]
    text = "\n".join(lines)
    parts = split_long_text(text, 200, 50)
    for line in lines:
        assert any(line in part for part in parts), f"Ligne perdue: {line}"


def test_split_without_newlines_preserves_word_boundaries():
    words = [f"token{i}" for i in range(40)]
    parts = split_long_text(" ".join(words), max_chars=70, overlap=15)

    assert len(parts) > 1
    assert all(len(part) <= 70 for part in parts)
    assert all(
        all(word.startswith("token") and word[5:].isdigit() for word in part.split())
        for part in parts
    )
    assert all(any(word in part.split() for part in parts) for word in words)


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
    assert page_map["1.2"] == [304, 305]


def test_wrapped_toc_is_discarded_before_body():
    """A wrapped TOC title must not create a section or leak into a chunk."""
    wrapped_title = "mapped features contributing to landscape continuity"
    raw = f"""## Page 302
Zone UM 8
1. Fonctions urbaines .............................................................5
1.3.5. Rules for {wrapped_title}
on the zoning map .................................................................9

## Page 303
Zone UM 8
1. Fonctions urbaines
General presentation of the chapter.
1.1. Valid rule
This is the actual rule text.
"""
    sections = extract_sections(raw)
    assert {section["number"] for section in sections} == {"1", "1.1"}
    assert all(
        wrapped_title not in section["title"] + section["content"]
        for section in sections
    )
    assert "actual rule text" in sections[-1]["content"]


def test_section_pages_include_continuation_pages():
    sections = extract_sections(SAMPLE_UM8_TEXT)
    section = next(item for item in sections if item["number"] == "1.2")
    assert section["content_pages"] == [304, 305]


def test_wrapped_lowercase_heading_continuation_is_part_of_title():
    raw = """## Page 303
Zone UM 8
1. Fonctions urbaines
Présentation du chapitre.
1.1. Implantation et caractéristiques
particulières des constructions
Les règles applicables sont décrites ci-dessous.
"""
    section = next(item for item in extract_sections(raw) if item["number"] == "1.1")
    assert section["title"] == "Implantation et caractéristiques particulières des constructions"
    assert section["content"] == "Les règles applicables sont décrites ci-dessous."


def test_chunk_pages_are_limited_to_text_covered_by_each_part():
    raw = """## Page 303
Zone UM 8
1. Fonctions urbaines
Présentation générale.
1.1. Règle test
Texte court.
1.2. Règle longue

## Page 304
Zone UM 8
1.2. Règle longue
Première phrase avec une longueur suffisante pour créer une coupure proche de la fin de page.

## Page 305
Zone UM 8
1.2. Règle longue
Deuxième phrase qui continue sur la page suivante et complète la disposition réglementaire.
"""
    sections = extract_sections(raw)
    page_map = {item["number"]: item["content_pages"] for item in sections}
    chunks = create_chunks(sections, page_map, "source", "v1", "UM 8", max_chars=100, overlap=20)
    long_chunks = [chunk for chunk in chunks if chunk["section_number"] == "1.2"]
    assert len(long_chunks) >= 2
    assert all(chunk["metadata"]["pages"] for chunk in long_chunks)
    assert any(chunk["metadata"]["pages"] == [304, 305] for chunk in long_chunks)
    assert len({chunk["id"] for chunk in long_chunks}) == len(long_chunks)


def test_saved_chunking_parameters_match_cli_values(tmp_path):
    output = tmp_path / "chunks.json"
    save_chunks([], str(output), max_chars=800, overlap=80)
    metadata = json.loads(output.read_text(encoding="utf-8"))["metadata"]
    assert metadata["max_chunk_chars"] == 800
    assert metadata["overlap_chars"] == 80




# =============================================================================
# Run
# =============================================================================

if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])

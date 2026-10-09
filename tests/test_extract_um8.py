import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from extract_um8 import (
    _validate_page_range,
    PAGE_EXTRACTOR_OVERRIDES,
    compare_extractions,
    normalize_extracted_text,
    resolve_page_range,
    select_chunk_source,
    validate_zone_boundary,
)


def test_zone_header_must_be_an_exact_line():
    pages = {
        303: "Zone UM 8\nTexte réglementaire.",
        304: "Zone UM 80\nTexte mentionnant Zone UM 8 dans le corps.",
    }
    assert validate_zone_boundary(pages) == [304]


def test_normalization_handles_hyphenated_line_wrap_and_whitespace():
    assert normalize_extracted_text("règle appli-\n cable\n ici") == "règle applicable ici"


def test_comparison_uses_normalized_similarity():
    result = compare_extractions({303: "texte régle-\nmentaire"}, {303: "texte réglementaire"})
    assert result["303"]["content_equal"] is False
    assert result["303"]["normalized_equal"] is True
    assert result["303"]["normalized_similarity"] == 1.0


def test_normalization_handles_typographic_subscript_spacing():
    assert normalize_extracted_text("hauteur H F et hauteur H T") == "hauteur HF et hauteur HT"


def test_invalid_page_ranges_are_rejected_not_truncated():
    _validate_page_range(1, 4, 4)
    with pytest.raises(ValueError, match="dépasse"):
        _validate_page_range(1, 5, 4)
    with pytest.raises(ValueError, match="invalide"):
        _validate_page_range(3, 2, 4)


def test_page_range_is_detected_when_no_manual_bounds_are_given(monkeypatch):
    import extract_um8

    calls = []

    def fake_find_boundaries(pdf_path, target_zone, next_zone):
        calls.append((pdf_path, target_zone, next_zone))
        return 303, 340

    monkeypatch.setattr(extract_um8, "find_zone_boundaries", fake_find_boundaries)
    assert resolve_page_range("source.pdf", None, None) == (303, 340)
    assert calls == [("source.pdf", "Zone UM 8", "Zone UM 9")]


def test_page_range_accepts_an_explicit_complete_override():
    assert resolve_page_range("source.pdf", 10, 20) == (10, 20)


def test_page_range_rejects_a_partial_manual_override():
    with pytest.raises(ValueError, match="--start et --end ensemble"):
        resolve_page_range("source.pdf", 10, None)


def test_chunk_source_selection_is_explicit_and_traceable():
    pypdf = {303: "pypdf 303", 324: "pypdf table"}
    pdfplumber = {303: "pdfplumber 303", 324: "detached table symbols"}
    selected, methods = select_chunk_source(pypdf, pdfplumber, {324: "pypdf"})
    assert selected == {303: "pdfplumber 303", 324: "pypdf table"}
    assert methods == {303: "pdfplumber", 324: "pypdf"}


def test_chunk_source_joins_spaced_height_subscripts():
    selected, _ = select_chunk_source(
        {327: "hauteur H F ou H T"}, {327: "hauteur H F ou H T"}, {327: "pypdf"}
    )
    assert selected[327] == "hauteur HF ou HT"


def test_chunk_source_repairs_unmapped_pdf_list_bullets():
    selected, _ = select_chunk_source(
        {308: "\ufffd\ufffd les centres d’hébergement"},
        {308: "\ufffd\ufffd les centres d’hébergement"},
        {308: "pypdf"},
    )
    assert selected[308] == "• les centres d’hébergement"


def test_chunk_source_selection_rejects_missing_override_page():
    with pytest.raises(ValueError, match="Texte manquant"):
        select_chunk_source({303: "text"}, {303: "text"}, {324: "pypdf"})


def test_visual_reviewed_subscript_pages_use_pypdf():
    assert PAGE_EXTRACTOR_OVERRIDES[327] == "pypdf"
    assert PAGE_EXTRACTOR_OVERRIDES[328] == "pypdf"

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import find_boundaries


class FakePage:
    def __init__(self, text):
        self.text = text

    def extract_text(self):
        return self.text


class FakeReader:
    pages = [
        FakePage("Une mention de Zone UM 8 au milieu d'un paragraphe."),
        FakePage("Zone UM 8\n1. Fonctions urbaines ..........5\n1.1. Article ..........5"),
        FakePage("Zone UM 8\nRèglement pièces écrites\n1. Fonctions urbaines\nPrésentation de la règle."),
        FakePage("Zone UM 8\nSuite de la règle."),
        FakePage("Zone UM 80\nPage d'une autre zone."),
        FakePage("Zone UM 9\nDébut de la zone suivante."),
        FakePage("Zone UM 8\nNe doit pas être retenu."),
    ]


def test_boundaries_ignore_mentions_toc_and_prefix_zone(monkeypatch):
    monkeypatch.setattr(find_boundaries.pypdf, "PdfReader", lambda _: FakeReader())
    assert find_boundaries.find_zone_boundaries("fake.pdf", "Zone UM 8", "Zone UM 9") == (3, 4)


def test_boundaries_fail_when_body_start_missing(monkeypatch):
    class NoBodyReader:
        pages = [FakePage("Zone UM 8\n1. Fonctions urbaines ..........5")]

    monkeypatch.setattr(find_boundaries.pypdf, "PdfReader", lambda _: NoBodyReader())
    with pytest.raises(ValueError, match="Début du corps"):
        find_boundaries.find_zone_boundaries("fake.pdf", "Zone UM 8", "Zone UM 9")

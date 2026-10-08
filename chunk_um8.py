#!/usr/bin/env python3
"""
Chunking du chapitre UM8 du règlement PLUi de Bordeaux Métropole.

Découpe le texte extrait en chunks respectant la structure juridique
hiérarchique (articles → sous-articles → sections) avec :
- Filtrage de la table des matières
- Nettoyage des artefacts PDF (headers répétés, séparateurs, etc.)
- Découpage des sections longues avec chevauchement
- IDs stables via SHA-256
- Métadonnées complètes (source, version, pages)
"""

import argparse
import hashlib
import json
import os
import re
import sys
from typing import Any


# --- Configuration par défaut --------------------------------------------------------

DEFAULT_INPUT = "extracted/um8_pdfplumber.txt"
DEFAULT_OUTPUT = "chunked/um8_chunks.json"
DEFAULT_ZONE = "UM 8"
DEFAULT_SOURCE = "PLUi de Bordeaux Métropole - Règlement écrit"
DEFAULT_VERSION = "version 30, publiée et en vigueur depuis le 12 mai 2026"
MAX_CHUNK_CHARS = 1500
OVERLAP_CHARS = 200


# --- Nettoyage -----------------------------------------------------------------------

# Lignes à supprimer entièrement
_NOISE_PATTERNS = [
    re.compile(r"^## Page \d+\s*$"),              # marqueurs de page markdown
    re.compile(r"^\s*-{3,}\s*$"),                   # séparateurs ---
    re.compile(r"^\s*11e?\s*modification\s*du\s*PLU\s*\d*\s*$", re.IGNORECASE),
]

# Headers répétés sur chaque page
_REPEATED_HEADERS = {"Zone UM 8", "Zone UM 9", "Règlement pièces écrites",
                      "Règlement pièces Ǹcrites"}


def is_noise_line(line: str) -> bool:
    """Retourne True si la ligne est un artefact à supprimer."""
    stripped = line.strip()
    if not stripped:
        return True
    if stripped in _REPEATED_HEADERS:
        return True
    return any(p.match(stripped) for p in _NOISE_PATTERNS)


def is_toc_line(line: str) -> bool:
    """
    Détecte les lignes de table des matières.
    Caractéristique : contiennent des points de suspension (…, ou .{3,})
    suivis d'un numéro de page.
    """
    stripped = line.strip()
    if re.search(r"\.{3,}\s*\d+\s*\d*\s*$", stripped):
        return True
    if re.search(r"…\s*\d+\s*$", stripped):
        return True
    return False


def clean_line(line: str) -> str:
    """Nettoyer une ligne de contenu (supprimer artefacts résiduels)."""
    # Supprimer les numéros de page en fin de ligne avec points
    line = re.sub(r"\s+\.{2,}\s*\d+\s*\d*\s*$", "", line)
    return line.strip()


# --- Détection des en-têtes de section -----------------------------------------------

_SECTION_RE = re.compile(r"^(\d+(?:\.\d+)*)\.\s+(.+)")


def parse_section_header(line: str) -> tuple[str, str] | None:
    """
    Si la ligne est un en-tête de section numéroté, retourne (numéro, titre).
    Sinon retourne None.
    """
    m = _SECTION_RE.match(line.strip())
    if m:
        return m.group(1), m.group(2).strip()
    return None


# --- Extraction des infos de page ----------------------------------------------------

def build_page_map(raw_text: str) -> dict[str, list[int]]:
    """
    Construit un dictionnaire { numéro_section: [pages] } en parcourant
    le texte brut page par page.
    """
    section_pages: dict[str, list[int]] = {}
    current_page: int | None = None

    for line in raw_text.split("\n"):
        page_match = re.match(r"^## Page (\d+)", line)
        if page_match:
            current_page = int(page_match.group(1))
            continue

        if current_page is None:
            continue

        cleaned = line.strip()
        if is_noise_line(cleaned) or is_toc_line(cleaned):
            continue

        header = parse_section_header(cleaned)
        if header:
            num = header[0]
            if num not in section_pages:
                section_pages[num] = []
            if current_page not in section_pages[num]:
                section_pages[num].append(current_page)

    for pages in section_pages.values():
        pages.sort()

    return section_pages


# --- Extraction des sections ---------------------------------------------------------

def extract_sections(raw_text: str) -> list[dict[str, Any]]:
    """
    Parcourt le texte ligne par ligne et regroupe le contenu sous chaque
    en-tête de section. Ignore les lignes de TdM et les artefacts.

    Gère le cas où le même en-tête apparaît sur plusieurs pages (pagination)
    en accumulant le contenu sous le même numéro de section.
    """
    sections: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    content_lines: list[str] = []

    def _flush():
        """Sauvegarder la section courante."""
        if current is not None:
            current["content"] = "\n".join(content_lines).strip()
            sections.append(current)

    for line in raw_text.split("\n"):
        # Ignorer les artefacts
        if is_noise_line(line):
            continue
        if is_toc_line(line):
            continue

        cleaned = clean_line(line)
        if not cleaned:
            continue

        header = parse_section_header(cleaned)
        if header:
            num, title = header
            # Même section qui continue sur la page suivante ?
            if current is not None and num == current["number"]:
                continue  # on garde le contenu accumulé

            # Nouvelle section → sauvegarder l'ancienne
            _flush()
            current = {"number": num, "title": title}
            content_lines = []
        else:
            if current is not None:
                content_lines.append(cleaned)

    _flush()
    return sections


# --- Création des chunks -------------------------------------------------------------

def make_chunk_id(source: str, version: str, section: str, content: str) -> str:
    """Hash SHA-256 tronqué à 16 hex pour ID stable."""
    blob = f"{source}|{version}|{section}|{content}"
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def split_long_text(text: str, max_chars: int, overlap: int) -> list[str]:
    """
    Découpe un texte long en morceaux de max_chars avec un chevauchement
    de overlap caractères. Le découpage se fait sur un saut de ligne
    pour ne pas couper en milieu de phrase.
    """
    if len(text) <= max_chars:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + max_chars
        if end >= len(text):
            chunks.append(text[start:].strip())
            break

        # Chercher le dernier saut de ligne avant la limite
        cut = text.rfind("\n", start, end)
        if cut <= start:
            cut = end  # pas de saut de ligne, couper au max

        chunks.append(text[start:cut].strip())
        start = max(start + 1, cut - overlap)  # reculer de overlap pour le chevauchement

    return [c for c in chunks if c]


def create_chunks(
    sections: list[dict],
    page_map: dict[str, list[int]],
    source: str,
    version: str,
    zone: str,
    max_chars: int = MAX_CHUNK_CHARS,
    overlap: int = OVERLAP_CHARS,
) -> list[dict[str, Any]]:
    """Transformer les sections en chunks avec métadonnées."""
    chunks = []

    for section in sections:
        num = section["number"]
        title = section["title"]
        content = section["content"]

        # Ignorer les sections sans contenu
        if not content.strip():
            continue

        parts = split_long_text(content, max_chars, overlap)

        for i, part in enumerate(parts):
            chunk_id = make_chunk_id(source, version, num, part)
            chunk = {
                "id": chunk_id,
                "type": "section",
                "section_number": num,
                "title": title,
                "content": part,
                "metadata": {
                    "source": source,
                    "version": version,
                    "zone": zone,
                    "pages": page_map.get(num, []),
                    "section_title": title,
                },
            }
            if len(parts) > 1:
                chunk["metadata"]["part"] = f"{i+1}/{len(parts)}"

            chunks.append(chunk)

    return chunks


# --- Sauvegarde ----------------------------------------------------------------------

def save_chunks(chunks: list[dict], path: str) -> None:
    """Écrire les chunks en JSON."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    output = {
        "chunks": chunks,
        "metadata": {
            "total_chunks": len(chunks),
            "chunking_method": "hierarchical_sections",
            "max_chunk_chars": MAX_CHUNK_CHARS,
            "overlap_chars": OVERLAP_CHARS,
            "description": "Chunks créés en respectant la structure hiérarchique du chapitre UM8",
        },
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)


# --- Point d'entrée ------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Chunking réglementaire du chapitre UM8")
    parser.add_argument("--input", default=DEFAULT_INPUT, help="Fichier texte extrait")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Fichier JSON de sortie")
    parser.add_argument("--zone", default=DEFAULT_ZONE, help="Nom de la zone")
    parser.add_argument("--max-chars", type=int, default=MAX_CHUNK_CHARS, help="Taille max d'un chunk")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"ERREUR : fichier introuvable — {args.input}", file=sys.stderr)
        sys.exit(1)

    print(f"Chunking : {args.input}")

    with open(args.input, "r", encoding="utf-8") as f:
        raw_text = f.read()

    # Construire la carte des pages
    page_map = build_page_map(raw_text)

    # Extraire les sections
    sections = extract_sections(raw_text)
    print(f"  Sections détectées : {len(sections)}")

    # Filtrer les sections vides
    sections_with_content = [s for s in sections if s["content"].strip()]
    empty_count = len(sections) - len(sections_with_content)
    if empty_count:
        print(f"  Sections vides ignorées : {empty_count}")

    # Créer les chunks
    chunks = create_chunks(
        sections_with_content, page_map,
        source=DEFAULT_SOURCE, version=DEFAULT_VERSION,
        zone=args.zone, max_chars=args.max_chars,
    )

    # Sauvegarder
    save_chunks(chunks, args.output)

    # Rapport
    content_lengths = [len(c["content"]) for c in chunks]
    multi_part = sum(1 for c in chunks if "part" in c.get("metadata", {}))

    print(f"\n{'='*50}")
    print(f"  Chunks créés : {len(chunks)}")
    print(f"    dont multi-parts (sections longues découpées) : {multi_part}")
    print(f"  Taille moyenne : {sum(content_lengths)/len(content_lengths):.0f} chars")
    print(f"  Min : {min(content_lengths)} chars")
    print(f"  Max : {max(content_lengths)} chars")
    print(f"  Sortie : {args.output}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""Build a reproducible FAISS dense index from the validated UM8 chunks."""

import argparse
import hashlib
import json
import os
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import sys
from typing import Any

import numpy as np

from embedding_config import (
    BATCH_SIZE,
    DEFAULT_CHUNKS_PATH,
    DEFAULT_INDEX_PATH,
    DEFAULT_METADATA_PATH,
    DEVICE,
    EMBEDDING_DIMENSION,
    MAX_SEQUENCE_TOKENS,
    MODEL_ID,
    MODEL_REVISION,
    PASSAGE_PREFIX,
    QUERY_PREFIX,
)


def validate_chunks(chunks: Any) -> list[dict[str, Any]]:
    """Reject malformed or ambiguous inputs before loading the model."""
    if not isinstance(chunks, list) or not chunks:
        raise ValueError("Le fichier doit contenir une liste non vide de chunks.")

    seen_ids: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for position, chunk in enumerate(chunks):
        if not isinstance(chunk, dict):
            raise ValueError(f"Chunk {position} : objet JSON attendu.")
        chunk_id = chunk.get("id")
        content = chunk.get("content")
        if (
            not isinstance(chunk_id, str)
            or not chunk_id.strip()
            or chunk_id != chunk_id.strip()
        ):
            raise ValueError(f"Chunk {position} : identifiant absent ou invalide.")
        if chunk_id in seen_ids:
            raise ValueError(f"Identifiant de chunk dupliqué : {chunk_id}")
        if not isinstance(content, str) or not content.strip():
            raise ValueError(f"Chunk {chunk_id} : contenu vide ou invalide.")
        section_number = chunk.get("section_number")
        if not isinstance(section_number, str) or not section_number.strip():
            raise ValueError(f"Chunk {chunk_id} : numéro de section absent ou invalide.")
        if not isinstance(chunk.get("title"), str) or not chunk["title"].strip():
            raise ValueError(f"Chunk {chunk_id} : titre absent ou invalide.")
        seen_ids.add(chunk_id)
        normalized.append(chunk)
    return normalized


def format_passage(chunk: dict[str, Any]) -> str:
    """Add legal section context and the prefix required by multilingual E5."""
    section = chunk["section_number"]
    title = chunk["title"].strip()
    content = chunk["content"].strip()
    return f"{PASSAGE_PREFIX}UM8, article {section} — {title}\n{content}"


def validate_embeddings(
    embeddings: Any,
    expected_rows: int,
    expected_dimension: int = EMBEDDING_DIMENSION,
) -> np.ndarray:
    """Enforce the matrix contract before it is handed to FAISS."""
    vectors = np.asarray(embeddings, dtype=np.float32)
    if vectors.ndim != 2:
        raise ValueError(f"Les embeddings doivent être une matrice 2D; reçu {vectors.shape}.")
    if vectors.shape != (expected_rows, expected_dimension):
        raise ValueError(
            f"Dimensions incorrectes : {vectors.shape}; attendu "
            f"({expected_rows}, {expected_dimension})."
        )
    if not np.isfinite(vectors).all():
        raise ValueError("Les embeddings contiennent NaN ou une valeur infinie.")
    norms = np.linalg.norm(vectors, axis=1)
    if not np.allclose(norms, 1.0, rtol=0.0, atol=1e-4):
        raise ValueError("Les embeddings doivent être normalisés en norme L2.")
    return np.ascontiguousarray(vectors)


def encode_chunks(
    chunks: list[dict[str, Any]],
    model: Any,
    expected_dimension: int = EMBEDDING_DIMENSION,
) -> np.ndarray:
    """Encode passages with normalized vectors; preserves input/index order."""
    passages = [format_passage(chunk) for chunk in chunks]
    embeddings = model.encode(
        passages,
        batch_size=BATCH_SIZE,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    return validate_embeddings(embeddings, len(chunks), expected_dimension)


def validate_passage_lengths(
    chunks: list[dict[str, Any]], tokenizer: Any, max_sequence_tokens: int
) -> list[int]:
    """Fail rather than silently embedding a truncated regulatory passage."""
    passages = [format_passage(chunk) for chunk in chunks]
    encoded = tokenizer(passages, add_special_tokens=True, truncation=False)
    lengths = [len(token_ids) for token_ids in encoded["input_ids"]]
    too_long = [
        (chunks[index]["id"], length)
        for index, length in enumerate(lengths)
        if length > max_sequence_tokens
    ]
    if too_long:
        example_ids = ", ".join(
            f"{chunk_id} ({length} tokens)" for chunk_id, length in too_long[:5]
        )
        raise ValueError(
            f"{len(too_long)} passages dépassent la limite de {max_sequence_tokens} tokens; "
            f"réduire les chunks avant indexation. Exemples : {example_ids}"
        )
    return lengths


def create_faiss_index(embeddings: np.ndarray, faiss_module: Any) -> Any:
    """Use exact inner-product search; for unit vectors it equals cosine similarity."""
    if embeddings.ndim != 2 or embeddings.shape[0] == 0:
        raise ValueError("Une matrice d'embeddings 2D non vide est requise.")
    index = faiss_module.IndexFlatIP(int(embeddings.shape[1]))
    index.add(embeddings)
    if index.ntotal != embeddings.shape[0]:
        raise RuntimeError("FAISS n'a pas indexé tous les vecteurs.")
    return index


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def package_version(distribution: str) -> str:
    try:
        return version(distribution)
    except PackageNotFoundError:
        return "unknown"


def build_metadata(
    chunks: list[dict[str, Any]],
    input_path: str,
    input_sha256: str,
    faiss_version: str,
    sentence_transformers_version: str,
    max_observed_tokens: int | None = None,
) -> dict[str, Any]:
    """Create a stable vector-position-to-chunk mapping and provenance record."""
    return {
        "schema_version": 1,
        "input": {
            "path": input_path,
            "sha256": input_sha256,
            "chunk_count": len(chunks),
        },
        "embedding": {
            "model_id": MODEL_ID,
            "model_revision": MODEL_REVISION,
            "dimension": EMBEDDING_DIMENSION,
            "max_sequence_tokens": MAX_SEQUENCE_TOKENS,
            "passage_prefix": PASSAGE_PREFIX,
            "query_prefix_for_phase_5": QUERY_PREFIX,
            "normalized_l2": True,
            "device": DEVICE,
            "max_observed_tokens": max_observed_tokens,
        },
        "index": {
            "library": "faiss-cpu",
            "type": "IndexFlatIP",
            "similarity": "inner product of L2-normalized vectors (cosine similarity)",
            "vector_count": len(chunks),
        },
        "software": {
            "numpy": np.__version__,
            "faiss_cpu": faiss_version,
            "sentence_transformers": sentence_transformers_version,
            "torch": package_version("torch"),
            "transformers": package_version("transformers"),
        },
        "vector_to_chunk_id": [chunk["id"] for chunk in chunks],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Construire l'index dense FAISS pour UM8")
    parser.add_argument("--chunks", default=DEFAULT_CHUNKS_PATH, help="JSON source des chunks")
    parser.add_argument("--index", default=DEFAULT_INDEX_PATH, help="Fichier FAISS de sortie")
    parser.add_argument("--metadata", default=DEFAULT_METADATA_PATH, help="Mapping et provenance JSON")
    args = parser.parse_args()

    chunks_path = Path(args.chunks)
    if not chunks_path.is_file():
        parser.error(f"Fichier de chunks introuvable : {chunks_path}")
    with chunks_path.open("r", encoding="utf-8") as file:
        payload = json.load(file)
    try:
        chunks = validate_chunks(payload.get("chunks") if isinstance(payload, dict) else None)
    except ValueError as error:
        parser.error(str(error))

    # Keep downloaded weights in an ignored, project-local cache by default.
    project_root = Path(__file__).resolve().parents[1]
    os.environ.setdefault("HF_HOME", str(project_root / ".cache" / "huggingface"))

    try:
        import faiss
        from sentence_transformers import SentenceTransformer
    except ImportError as error:
        print(
            "Dépendances manquantes. Installer requirements.txt dans l'environnement actif.",
            file=sys.stderr,
        )
        raise SystemExit(1) from error

    print(f"Chargement du modèle {MODEL_ID} ({MODEL_REVISION[:8]}) sur {DEVICE}...")
    model = SentenceTransformer(MODEL_ID, revision=MODEL_REVISION, device=DEVICE)
    actual_dimension = model.get_embedding_dimension()
    if actual_dimension != EMBEDDING_DIMENSION:
        raise RuntimeError(
            f"Dimension du modèle inattendue : {actual_dimension}; "
            f"attendu {EMBEDDING_DIMENSION}."
        )

    token_lengths = validate_passage_lengths(
        chunks, model[0].tokenizer, model.max_seq_length
    )
    if model.max_seq_length != MAX_SEQUENCE_TOKENS:
        raise RuntimeError(
            f"Limite de tokens inattendue : {model.max_seq_length}; "
            f"attendu {MAX_SEQUENCE_TOKENS}."
        )
    vectors = encode_chunks(chunks, model)
    index = create_faiss_index(vectors, faiss)

    index_path = Path(args.index)
    metadata_path = Path(args.metadata)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(index_path))
    reloaded_index = faiss.read_index(str(index_path))
    if reloaded_index.ntotal != len(chunks) or reloaded_index.d != EMBEDDING_DIMENSION:
        raise RuntimeError("L'index sauvegardé ne passe pas le contrôle de relecture.")
    metadata = build_metadata(
        chunks=chunks,
        input_path=args.chunks,
        input_sha256=sha256_file(chunks_path),
        faiss_version=package_version("faiss-cpu"),
        sentence_transformers_version=package_version("sentence-transformers"),
        max_observed_tokens=max(token_lengths),
    )
    with metadata_path.open("w", encoding="utf-8", newline="\n") as file:
        json.dump(metadata, file, indent=2, ensure_ascii=False)
        file.write("\n")

    print(
        f"Index créé : {index.ntotal} vecteurs, dimension {vectors.shape[1]}, "
        f"IndexFlatIP (cosinus sur vecteurs normalisés)."
    )
    print(f"Longueur maximale d'un passage : {max(token_lengths)}/{model.max_seq_length} tokens.")
    print(f"FAISS : {index_path}")
    print(f"Mapping : {metadata_path}")


if __name__ == "__main__":
    main()

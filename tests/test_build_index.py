import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from build_index import (
    build_metadata,
    create_faiss_index,
    encode_chunks,
    format_passage,
    validate_chunks,
    validate_embeddings,
    validate_passage_lengths,
)


class FakeModel:
    def __init__(self, vectors):
        self.vectors = vectors
        self.inputs = None
        self.kwargs = None

    def encode(self, sentences, **kwargs):
        self.inputs = sentences
        self.kwargs = kwargs
        return self.vectors


class FakeIndex:
    def __init__(self, dimension):
        self.dimension = dimension
        self.ntotal = 0
        self.vectors = None

    def add(self, vectors):
        self.vectors = vectors.copy()
        self.ntotal = len(vectors)


class FakeFaiss:
    IndexFlatIP = FakeIndex


class FakeTokenizer:
    def __call__(self, passages, **kwargs):
        assert kwargs["truncation"] is False
        return {"input_ids": [[1, 2] for _ in passages]}


@pytest.fixture
def sample_chunks():
    return [
        {
            "id": "chunk-a",
            "section_number": "1.1",
            "title": "Destination des constructions",
            "content": "Les définitions sont communes aux zones.",
        },
        {
            "id": "chunk-b",
            "section_number": "1.3",
            "title": "Conditions particulières",
            "content": "Les constructions sont soumises aux conditions suivantes.",
        },
    ]


def test_passage_format_includes_e5_prefix_and_section_context(sample_chunks):
    assert format_passage(sample_chunks[0]) == (
        "passage: UM8, article 1.1 — Destination des constructions\n"
        "Les définitions sont communes aux zones."
    )


def test_validate_chunks_rejects_duplicate_ids(sample_chunks):
    with pytest.raises(ValueError, match="dupliqué"):
        validate_chunks([sample_chunks[0], sample_chunks[0]])


def test_validate_chunks_rejects_empty_content(sample_chunks):
    malformed = [dict(sample_chunks[0], content=" ")]
    with pytest.raises(ValueError, match="contenu vide"):
        validate_chunks(malformed)


@pytest.mark.parametrize(
    "field,value,error",
    [
        ("id", "   ", "identifiant absent ou invalide"),
        ("id", " chunk-a ", "identifiant absent ou invalide"),
        ("section_number", "   ", "numéro de section absent ou invalide"),
    ],
)
def test_validate_chunks_rejects_blank_or_padded_identity_fields(
    sample_chunks, field, value, error
):
    malformed = [dict(sample_chunks[0], **{field: value})]
    with pytest.raises(ValueError, match=error):
        validate_chunks(malformed)


def test_encode_chunks_uses_normalized_vectors_and_preserves_order(sample_chunks):
    vectors = np.asarray([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)
    model = FakeModel(vectors)
    result = encode_chunks(sample_chunks, model, expected_dimension=2)

    assert result.dtype == np.float32
    assert result.flags.c_contiguous
    assert model.inputs[0].startswith("passage: UM8, article 1.1")
    assert model.inputs[1].startswith("passage: UM8, article 1.3")
    assert model.kwargs["normalize_embeddings"] is True
    assert model.kwargs["batch_size"] == 32


@pytest.mark.parametrize(
    "vectors,rows,dimension,error",
    [
        (np.ones(3), 1, 3, "2D"),
        (np.ones((2, 3)), 1, 3, "Dimensions incorrectes"),
        (np.asarray([[0.0, 0.0]], dtype=np.float32), 1, 2, "normalisés"),
        (np.asarray([[np.nan, 1.0]], dtype=np.float32), 1, 2, "NaN"),
    ],
)
def test_validate_embeddings_rejects_invalid_matrix(vectors, rows, dimension, error):
    with pytest.raises(ValueError, match=error):
        validate_embeddings(vectors, rows, dimension)


def test_faiss_index_uses_inner_product_and_checks_vector_count():
    vectors = np.asarray([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)
    index = create_faiss_index(vectors, FakeFaiss)

    assert index.dimension == 2
    assert index.ntotal == 2
    np.testing.assert_array_equal(index.vectors, vectors)


def test_metadata_maps_vector_positions_to_stable_chunk_ids(sample_chunks):
    metadata = build_metadata(
        sample_chunks,
        input_path="data/chunked/um8_chunks.json",
        input_sha256="a" * 64,
        faiss_version="1.15.1",
        sentence_transformers_version="6.1.0",
    )

    assert metadata["vector_to_chunk_id"] == ["chunk-a", "chunk-b"]
    assert metadata["index"]["type"] == "IndexFlatIP"
    assert metadata["embedding"]["normalized_l2"] is True
    assert metadata["input"]["chunk_count"] == 2


def test_validate_passage_lengths_reports_observed_token_count(sample_chunks):
    lengths = validate_passage_lengths(sample_chunks, FakeTokenizer(), max_sequence_tokens=3)
    assert lengths == [2, 2]


def test_validate_passage_lengths_rejects_silent_truncation(sample_chunks):
    class TooLongTokenizer:
        def __call__(self, passages, **kwargs):
            return {"input_ids": [[1, 2, 3, 4] for _ in passages]}

    with pytest.raises(ValueError, match="dépassent la limite"):
        validate_passage_lengths(sample_chunks, TooLongTokenizer(), max_sequence_tokens=3)

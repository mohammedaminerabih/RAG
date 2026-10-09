"""Fixed, documented settings for the UM8 dense-index baseline."""

MODEL_ID = "intfloat/multilingual-e5-small"
# Pin an immutable Hugging Face revision so a rebuild does not silently use new weights.
MODEL_REVISION = "5697a65b0a002a92fe8c4fc9d495303ffff9c7d2"
EMBEDDING_DIMENSION = 384
MAX_SEQUENCE_TOKENS = 512
BATCH_SIZE = 32
DEVICE = "cpu"
PASSAGE_PREFIX = "passage: "
QUERY_PREFIX = "query: "

DEFAULT_CHUNKS_PATH = "data/chunked/um8_chunks.json"
DEFAULT_INDEX_PATH = "data/index/um8.faiss"
DEFAULT_METADATA_PATH = "data/index/um8_index_metadata.json"
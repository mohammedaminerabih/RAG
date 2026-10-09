# Bordeaux PLUi RAG — UM8 Written Regulations

A document-retrieval and grounded question-answering project based on the written regulations for Zone UM8 in the Bordeaux Métropole local urban plan (PLUi). This is a research prototype, **not** a tool for determining whether a property or project complies with planning rules.

## Current status

Phases 0–4 are complete. The project can identify the UM8 pages in the source PDF, extract and chunk the written regulations, create embeddings, and build a local FAISS index. Query-time retrieval, the evaluation datasets, LLM answers, and the API are **not implemented yet**; they are planned for later phases.

- The UM8 body spans physical PDF pages **303–340**: 38 pages. The PDF page number is not the same as the printed page number inside the document.
- Extraction found 98 sections, including 13 empty sections that were skipped, and produced **130 chunks**. Chunk lengths range from 62 to 1,500 characters; the median is 947.5.
- **59 automated tests pass** across boundary detection, extraction, chunking, and index validation.
- The tables on PDF pages 322 and 324 were visually reviewed. Text extraction does not reliably preserve their row/column relationships, so questions that depend on those relationships are excluded from the initial evaluation set.
- pypdf is selected explicitly on pages 324, 327, and 328. On pages 327–328 it preserves the `HF`/`HT` height markers better than pdfplumber.
- The local dense index contains **130 normalized 384-dimensional vectors**, built with the pinned `intfloat/multilingual-e5-small` model and FAISS `IndexFlatIP`. The longest passage is 464/512 model tokens.

## Pipeline

```text
Official written-regulation PDF
        ↓
Page detection and extraction checks (pypdf + pdfplumber)
        ↓
Article-aware chunks with source pages and stable IDs
        ↓
E5 passage embeddings → exact FAISS index
        ↓
Next: dense retrieval → evaluation → hybrid comparison → cited answers → API
```

The pipeline is implemented directly in Python, without LangChain or LlamaIndex. The PDF, local model cache, virtual environment, and generated `data/index/` directory are ignored by Git. The index and its metadata are recreated locally by `src/build_index.py`.

## Key files

```text
data/
  243300316_reglement_20260505.pdf  # Local source PDF; ignored by Git
  extracted/                        # Extraction outputs and comparison reports
  chunked/um8_chunks.json           # 130 chunks used to build the index
  index/                            # Local FAISS index + metadata; ignored by Git
src/
  find_boundaries.py                # Detect physical PDF pages for a zone
  extract_um8.py                    # Extract and compare PDF text
  chunk_um8.py                      # Parse articles and create chunks
  embedding_config.py              # Pinned embedding model configuration
  build_index.py                    # Embed chunks and build/save the FAISS index
tests/                              # Automated tests for the implemented pipeline
requirements.txt
SOURCES.MANIFEST                    # Source URL, version, and checksum
```

## Reproduce the current pipeline (PowerShell)

The source PDF is intentionally not committed because it is about 147 MB. Download only the written-regulation document, not the full archive:

```powershell
New-Item -ItemType Directory -Force data | Out-Null
Invoke-WebRequest `
  -Uri "https://www.geoportail-urbanisme.gouv.fr/api/document/0b6c6621184959caf3fa5b684f929657/files/243300316_reglement_20260505.pdf" `
  -OutFile "data/243300316_reglement_20260505.pdf"
Get-FileHash data/243300316_reglement_20260505.pdf -Algorithm SHA256
```

Compare the checksum with `SOURCES.MANIFEST`, then install and run the pipeline:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest -q -p no:cacheprovider
python src/extract_um8.py
python src/chunk_um8.py
python src/build_index.py
```

`extract_um8.py` detects the zone boundaries automatically. `find_boundaries.py` can also be run independently to inspect the detected page range. If specifying extraction pages manually, both `--start` and `--end` are required.

The first index build downloads the pinned embedding model into `.cache/huggingface/`; this public model does not require an LLM API key. Passage vectors use the E5 `passage:` prefix. The future query-retrieval phase must use the corresponding `query:` prefix.

## Corpus scope and limitations

The source is version 30 of the written, zone-by-zone regulations, published on 12 May 2026. The corpus does not include zoning maps, prescriptions, easements, appendices, or contextual planning documents. Article 1.1 includes definitions explicitly stated to be common across zones, but the project does not claim to cover every general PLUi rule.

Some clauses refer to absent maps, prescriptions, or appendices. Questions that depend on those materials must be excluded or answered with an abstention; the system must not infer the missing rule.

Extraction similarity is a lexical measure. It can reveal missing words, but it cannot validate a table's structure or legal meaning. The tables on pages 322 and 324 remain out of scope for questions requiring reliable cell relationships. Other tables must not be treated as validated merely because their lexical score is high.

## Project phases

**Completed:**

0. Scope and corpus definition
1. Source collection and provenance
2. PDF extraction and quality checks
3. Article parsing and chunking
4. Embeddings and local FAISS index

**Planned:**

5. Dense question retrieval
6. Retrieval evaluation: about 10 development questions and a separate, frozen set of 20–30 questions; Recall@k and MRR
7. Compare dense retrieval with BM25-based hybrid retrieval on the development set; freeze the choice before final evaluation
8. Generate source-grounded answers with validated citations and abstention
9. Audit answer faithfulness, citation correctness, and abstentions
10. Deliver a tested FastAPI service in Docker

Reranking is optional and will only be considered after retrieval has been measured. The project is currently at the end of phase 4; the planned phases are not implemented yet.

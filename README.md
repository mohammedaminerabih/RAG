# RAG Project - PLUi Bordeaux Métropole (Zone UM8)

## Objective
Build a Retrieval-Augmented Generation (RAG) system for question answering over the written regulation of the Bordeaux Métropole PLUi, specifically focusing on the UM8 zoning district.

## Architecture & Stack
This project intentionally avoids heavy frameworks like LangChain or LlamaIndex in favor of a raw, transparent pipeline.
- **Extraction**: `pdfplumber` and `pypdf`
- **Chunking**: Custom hierarchical legal parser (splits by articles and sections)
- **Embedding/Retrieval**: Sentence Transformers + FAISS (Phase 4 - upcoming)
- **Generation**: Direct API calls to a designated LLM with strict context constraints (Phase 6 - upcoming)
- **Interface**: TBD (Streamlit / Gradio)

## Directory Structure
- `data/` - Raw PLUi PDF (git-ignored due to size)
- `extracted/` - Parsed text outputs from the PDF
- `chunked/` - JSON chunks ready for vectorization
- `tests/` - Test suite for the pipeline
- `useful files/` - Legacy planning documents
- `journal.md` - Complete chronological project log (in French)
- `plan.tex` - LaTeX project management and architecture plan (in French)
- `SOURCES.MANIFEST` - Traceability matrix for the legal data

## Current Status
- ✅ **Phase 0 & 1**: Setup and Corpus validation
- ✅ **Phase 2 & 3**: PDF Extraction and Regulatory Chunking (cleaned and tested)
- ⏳ **Phase 4**: Vector Indexing

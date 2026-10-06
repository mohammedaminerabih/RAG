# RAG Project - Work Rules

## Core Principles
- **One phase at a time**: Announce the current phase and wait for explicit authorization before proceeding to the next phase
- **Documentation update**: At the end of each phase, update both `plan.tex` and `journal.md` with decisions, alternatives, problems/solutions, numerical results, and interview questions
- **Evaluation-first**: Define expected answers before comparing systems; never optimize on the final test set
- **Separate concerns**: Distinguish retrieval quality, generation fidelity, and citation accuracy; no single metric proves legal compliance
- **Honest reporting**: Report failures, null gains, and uncertainties related to the 20-30 question evaluation set

## Technical Requirements
- **Manual pipeline**: Python implementation without LangChain or LlamaIndex initially
- **Retrieval**: Sentence Transformers + FAISS as baseline; Chroma as alternative if justified by concrete persistence/metadata needs
- **Generation**: Single fixed-model hosted API with spending limits and token constraints; API key in `.env` (ignored by Git)
- **Testing**: Deterministic mock LLM client; unit tests make zero network calls and consume no budget
- **Citations**: Code resolves chunk identifiers to real sources/pages; LLM never fabricates links or references
- **Security**: No secrets in Git; API key stored in `.env` which must be ignored by Git before any real key is created

## Reference Document
- **plan.tex** is the unique reference for project planning and phase definitions. All phase descriptions, durations, deliverables, and success criteria are defined there.
- **journal.md** is updated at the end of each completed phase with execution details.
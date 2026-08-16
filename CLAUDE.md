# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Hybrid RAG over local PDFs. Dense retrieval (ChromaDB + Ollama embeddings) fused with BM25 lexical rerank (bm25s). Chunk text + metadata persisted in MongoDB; embeddings persisted in Chroma.

Python 3.14. Managed with `uv` (`.python-version` pins 3.14, `uv.lock` present, no `requirements.txt`).

## Commands

Install / sync deps:
```bash
uv sync
```

Run ingestion against `./docs/pdfs/`:
```bash
uv run python ingestion.py
```
`ingestion.py` reads `DEFAULT_COLLECTION` from `.env` (defaults to `test`) and writes to Chroma (`./chroma/`) and MongoDB (`rag_db.document_chunks` on `mongodb://localhost:27017/`).

Smoke-test the search pipeline:
```bash
uv run python -c "from reranker import search; print(search('your query'))"
```

No test suite, linter, or formatter configured in `pyproject.toml`. No CI.

## Prereqs (external services)

- MongoDB running on `localhost:27017` (URI hardcoded in `ingestion.py:35` and `reranker.py:11` — duplicated, not env-driven).
- Ollama running on `OLLAMA_BASE_URL` with the `OLLAMA_EMBED_MODEL` pulled (default `nomic-embed-text`).

## Environment

`.env` keys consumed:
- `CHROMA_PATH` — Chroma persistent dir (default `./chroma`).
- `OLLAMA_BASE_URL` — Ollama server (default `http://localhost:11434`).
- `OLLAMA_EMBED_MODEL` — embedding model name (default `nomic-embed-text`).
- `DEFAULT_COLLECTION` — Chroma collection name used by ingest + search (default `test`).

`.env` is gitignored. `.env.example` does not exist — copy from a teammate or recreate from the keys above.

## Architecture

Data flow at ingest time:

```
docs/pdfs/*.pdf
  └─ Convert.langchain_load_pdf (document_parser.py)
       └─ OpenDataLoaderPDFLoader → markdown Document chunks
            ├─ MongoDB: rag_db.document_chunks  (full content + source metadata)
            └─ VectorStore.ingest (vectorsearch.py)
                  └─ ChromaDB collection: ids + embeddings + metadata
```

Data flow at query time (`reranker.search`):

```
query
  ├─ VectorStore.search(query, k)  → Chroma top-k ids
  ├─ MongoDB find({_id: {$in: ids}})  → hydrate DocumentChunk rows
  └─ IndexSearch(BM25).index(texts) → IndexSearch.search(query)
        └─ Reorder hydrated chunks by BM25 score, return ordered list
```

Key invariants:
- `_id` in MongoDB matches the id stored in Chroma. Built as `f"{source}_page{page}_chunk_{chunk_id}"` in `ingestion.py:71-75`. Reindexing relies on this stability — if the formula changes, dedup breaks.
- Chroma `metadata` and MongoDB `source` come from `OpenDataLoaderPDFLoader` metadata; MongoDB stores the authoritative `content`, Chroma only stores it as a convenience in metadata.
- VectorStore and IndexSearch are stateless wrappers — both are instantiated per call in `reranker.py` (no pooling). IndexSearch rebuilds the BM25 index on every query, which is fine for small k but won't scale.

## Module map

- `document_parser.py` — PDF → langchain `Document` list. Also exposes `document_to_lists` (splits into content/metadata lists for ingestion). `Convert.pdf_to_markdown` writes markdown to `./output/` (used for debugging, not part of the RAG path).
- `vectorsearch.py` — `VectorStore` class. Uses cosine HNSW space. `upsert` (not `add`) so re-ingestion is idempotent.
- `indexsearch.py` — `IndexSearch` class over `bm25s.BM25`. Has `load`/`save` but no caller persists the index yet.
- `ingestion.py` — `ingest_pdfs(docs_path)`. Builds ids, writes MongoDB, then calls `VectorStore.ingest`. Module-level `if __name__ == "__main__"` runs against `./docs/pdfs/`.
- `reranker.py` — `search(query, k=10)`. The only public query API.
- `main.py` — placeholder, prints a greeting.

## Known gaps

- `get_client()` is duplicated in `ingestion.py` and `reranker.py` instead of shared.
- MongoDB URI is hardcoded — not env-driven like Chroma/Ollama.
- BM25 index is rebuilt per query; no persisted state.
- No tests, no linter, no formatter configured.

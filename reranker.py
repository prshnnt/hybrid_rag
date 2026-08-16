from vectorsearch import VectorStore
from indexsearch import IndexSearch
from db import get_client, DEFAULT_DB, DEFAULT_COLLECTION
from ingestion import DocumentChunk
from typing import List
from pathlib import Path
import os
from dotenv import load_dotenv
load_dotenv()

BM25_INDEX_PATH = os.getenv("BM25_INDEX_PATH", "")


def search(query: str, k: int = 10):
    vectorstore = VectorStore()

    collection_name = os.environ.get(
        "DEFAULT_COLLECTION",
        "test"
    )

    # Vector search
    results = vectorstore.search(
        collection_name=collection_name,
        query=query,
        k=k
    )

    ids = results["ids"][0]

    if not ids:
        return []

    # MongoDB
    with get_client() as client:
        db = client[DEFAULT_DB]
        collection = db[DEFAULT_COLLECTION]

        mongo_docs = collection.find({
            "_id": {
                "$in": ids
            }
        })

        docs = [
            DocumentChunk.model_validate(doc)
            for doc in mongo_docs
        ]


    docs_by_id = {
        doc.id: doc
        for doc in docs
    }

    ordered_docs = [
        docs_by_id[chunk_id]
        for chunk_id in ids
        if chunk_id in docs_by_id
    ]

    # Reranking
    texts = [
        doc.content
        for doc in ordered_docs
    ]

    index_path = Path(BM25_INDEX_PATH) if BM25_INDEX_PATH else None
    if index_path and index_path.exists():
        indexsearch = IndexSearch.load(str(index_path))
    else:
        indexsearch = IndexSearch()
        indexsearch.index(texts)
        if index_path:
            indexsearch.save(str(index_path))

    index_ids = indexsearch.search(query, k=k)

    ranked_docs = [
        ordered_docs[i]
        for i in index_ids.documents[0]
    ]

    return ranked_docs
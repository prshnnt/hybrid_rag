from vectorsearch import VectorStore
from indexsearch import IndexSearch
from pymongo import MongoClient
from ingestion import DocumentChunk
from typing import List
import os
from dotenv import load_dotenv
load_dotenv()

def get_client():
    return MongoClient("mongodb://localhost:27017/")
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
        db = client["rag_db"]
        collection = db["document_chunks"]

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

    indexsearch = IndexSearch()
    indexsearch.index(texts)

    index_ids = indexsearch.search(query)

    ranked_docs = [
        ordered_docs[i]
        for i in index_ids.documents[0]
    ]

    return ranked_docs
from document_parser import Convert, document_to_lists
from pymongo import MongoClient
from vectorsearch import VectorStore

import os
from dotenv import load_dotenv

from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, Field

load_dotenv()

class Source(BaseModel):
    filename: str
    path: str
    page: int


class DocumentChunk(BaseModel):
    id: str = Field(alias="_id")
    document_id: str
    content: str
    source: Source
    chunk_id: int
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    model_config = ConfigDict(
        populate_by_name=True
    )


def get_client():
    return MongoClient("mongodb://localhost:27017/")

def ingest_pdfs(docs_path: str):

    print("Loading VectorStore....")
    vector_store = VectorStore()
    print("Loaded VectorStore.")

    collection_name = os.environ.get(
        "DEFAULT_COLLECTION",
        "test"
    )

    print("Loading Documents....")
    docs = Convert.langchain_load_pdf(
        path=docs_path,
        format="markdown"
    )
    print("Loaded Documents.")

    # data
    content, metadatas = document_to_lists(docs)

    ids = []
    # MongoDB documents for injestion
    mongo_documents = []

    for doc in docs:

        source = str(doc.metadata["source"])

        page = doc.metadata.get("page", 1)

        chunk_id = doc.metadata.get("chunk_id", 0)

        # Unique ID for this chunk
        doc_id = (
            f"{source}"
            f"_page{page}"
            f"_chunk_{chunk_id}"
        )

        ids.append(doc_id)

        document_chunk = DocumentChunk(
            id=doc_id,

            document_id=source,

            content=doc.page_content,

            source={
                "filename": source,
                "path": os.path.join(
                    docs_path,
                    source
                ),
                "page": page
            },

            chunk_id=chunk_id
        )

        # Convert Pydantic model -> MongoDB document
        mongo_documents.append(
            document_chunk.model_dump(
                by_alias=True
            )
        )

    print("Saving Documents to MongoDB....")
    with get_client() as client:
        db = client["rag_db"]
        collection = db["document_chunks"]

        if mongo_documents:
            collection.insert_many(
                mongo_documents
            )

    print("Saved Documents to MongoDB.")

    print("Ingesting Documents into VectorStore....")
    vector_store.ingest(
        collection_name=collection_name,
        ids=ids,
        content=content,
        metadatas=metadatas
    )
    print("Ingested Documents.")


# -----------------------------
# Main
# -----------------------------

if __name__ == "__main__":
    ingest_pdfs("./docs/pdfs/")
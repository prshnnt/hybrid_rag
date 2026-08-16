from document_parser import Convert, document_to_lists
from db import get_client, DEFAULT_DB, DEFAULT_COLLECTION
from vectorsearch import VectorStore

import os
from dotenv import load_dotenv

from datetime import datetime, timezone
from pymongo.errors import BulkWriteError
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


def ingest_pdfs(docs_path: str, replace: bool = True):

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
    source_paths = set()

    for doc in docs:

        source = str(doc.metadata["source"])

        page = doc.metadata.get("page", 1)

        chunk_id = doc.metadata.get("chunk_id", 0)

        # ID format is load-bearing for dedup + external references.
        # Do not change without coordinating a full reindex.
        doc_id = (
            f"{source}"
            f"_page{page}"
            f"_chunk_{chunk_id}"
        )

        ids.append(doc_id)
        source_paths.add(source)

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
        db = client[DEFAULT_DB]
        collection = db[DEFAULT_COLLECTION]

        if replace and source_paths:
            deleted = collection.delete_many(
                {"source.filename": {"$in": list(source_paths)}}
            )
            print(f"Deleted {deleted.deleted_count} existing chunks for re-ingest.")

        if mongo_documents:
            try:
                collection.insert_many(
                    mongo_documents,
                    ordered=False
                )
            except BulkWriteError as e:
                # Only reachable when replace=False and a duplicate _id appears.
                skipped = len(e.details.get("writeErrors", []))
                print(f"insert_many: {skipped} duplicates skipped.")

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
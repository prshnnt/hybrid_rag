from document_parser import Convert , document_to_lists
from vectorsearch import VectorStore
import os 
from dotenv import load_dotenv
load_dotenv()

def ingest_pdfs(docs_path):
    print("Loading VectorStore....")
    vectorStore = VectorStore()
    print("Loaded VectorStore .")
    collection_name = os.environ.get("DEFAULT_COLLECTION","test")
    print("Loading Documents....")
    docs = Convert.langchain_load_pdf(
        path=docs_path,
        format="markdown"
    )
    print("Loaded Documents .")
    content , metadatas = document_to_lists(docs)
    ids = [str(metadata["page"]) for metadata in metadatas]
    print("Ingesting Documents....")
    vectorStore.ingest(
        collection_name=collection_name,
        ids=ids,
        content=content,
        metadatas=metadatas
        )
    print("Ingested Documents .")

if __name__ == "__main__":
    ingest_pdfs("./docs/pdfs/")
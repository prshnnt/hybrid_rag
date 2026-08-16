import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

DEFAULT_DB = "rag_db"
DEFAULT_COLLECTION = "document_chunks"


def mongo_uri() -> str:
    return os.getenv("MONGO_URI", "mongodb://localhost:27017/")


def get_client() -> MongoClient:
    return MongoClient(mongo_uri())


def get_chunks_collection():
    return get_client()[DEFAULT_DB][DEFAULT_COLLECTION]

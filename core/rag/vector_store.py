from __future__ import annotations

from langchain_chroma import Chroma
from langchain_core.documents import Document

from core.config import CHROMA_DIR
from core.exceptions import VectorStoreError

COLLECTION_NAME = "knowledge_base"


def get_vector_store(embedding_function) -> Chroma:
    try:
        return Chroma(
            collection_name=COLLECTION_NAME,
            embedding_function=embedding_function,
            persist_directory=str(CHROMA_DIR),
        )
    except Exception as exc:  # noqa: BLE001
        raise VectorStoreError(f"Failed to open vector store: {exc}") from exc


def add_documents(vector_store: Chroma, documents: list[Document]) -> None:
    if not documents:
        raise VectorStoreError("No document chunks to add to the vector store.")
    try:
        vector_store.add_documents(documents)
    except Exception as exc:  # noqa: BLE001
        raise VectorStoreError(f"Failed to add documents to vector store: {exc}") from exc


def delete_by_source_id(vector_store: Chroma, source_id: str) -> None:
    try:
        vector_store._collection.delete(where={"source_id": source_id})
    except Exception as exc:  # noqa: BLE001
        raise VectorStoreError(f"Failed to delete vectors for source {source_id}: {exc}") from exc


def similarity_search(vector_store: Chroma, query: str, k: int = 4) -> list[Document]:
    try:
        return vector_store.similarity_search(query, k=k)
    except Exception as exc:  # noqa: BLE001
        raise VectorStoreError(f"Similarity search failed: {exc}") from exc

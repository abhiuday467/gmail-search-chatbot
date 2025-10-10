"""ChromaDB vector store integration."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence
from uuid import uuid4

import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.utils import embedding_functions
from langchain_core.documents import Document

from .config import Settings, get_settings


class VectorStore:
    """Wrapper around ChromaDB persistent client."""

    def __init__(
        self,
        settings: Settings | None = None,
        collection_name: str = "gmail_messages",
    ) -> None:
        self._settings = settings or get_settings()
        self._collection_name = collection_name
        self._client = self._create_client(self._settings.vector_store_dir)
        self._collection = self._client.get_or_create_collection(
            name=self._collection_name,
            embedding_function=self._create_embedding_function(),
        )

    def _create_client(self, path: Path) -> chromadb.PersistentClient:
        path.mkdir(parents=True, exist_ok=True)
        return chromadb.PersistentClient(path=str(path))

    def _create_embedding_function(self):
        provider = (self._settings.embedding_provider or "openai").lower()
        if provider == "openai":
            if not self._settings.openai_api_key:
                raise ValueError("OPENAI_API_KEY must be configured when using the OpenAI embedding provider.")
            return embedding_functions.OpenAIEmbeddingFunction(
                api_key=self._settings.openai_api_key,
                model_name="text-embedding-3-small",
            )
        raise ValueError(f"Unsupported embedding provider: {self._settings.embedding_provider}")

    @property
    def collection(self) -> Collection:
        return self._collection

    def add_documents(self, documents: Sequence[Document]) -> None:
        ids = []
        metadatas = []
        texts = []
        for doc in documents:
            ids.append(str(doc.metadata.get("id", uuid4())))
            metadatas.append(doc.metadata)
            texts.append(doc.page_content)
        if not texts:
            return
        self._collection.upsert(ids=ids, metadatas=metadatas, documents=texts)

    def persist(self) -> None:
        self._client.persist()

    def similarity_search(self, query: str, k: int = 4) -> list[Document]:
        results = self._collection.query(query_texts=[query], n_results=k)
        documents: list[Document] = []
        for doc, metadata, doc_id in zip(
            results.get("documents", [[]])[0],
            results.get("metadatas", [[]])[0],
            results.get("ids", [[]])[0],
        ):
            documents.append(Document(page_content=doc, metadata={**(metadata or {}), "id": doc_id}))
        return documents

"""Vector store management for the ARAS Recommendation Agent's RAG stack.

This module is the third stage of the Retrieval-Augmented Generation
pipeline: it takes the chunked `Document` objects produced by
`recommendation.rag.ingestion`, embeds them via
`recommendation.rag.embeddings.EmbeddingManager`, and persists them in
a local ChromaDB collection so a future Retriever component can query
them by similarity.

This module MUST NOT:
    - load or split documents
    - retrieve documents for a query
    - generate recommendations
    - call any LLM

Those responsibilities belong to other RAG components (ingestion,
retriever, generation) built around this one.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from langchain_chroma import Chroma
from langchain_core.documents import Document

from recommendation.rag.embeddings import EmbeddingManager

# Persisted under recommendation/chroma_db/, resolved relative to this
# file rather than the current working directory, so the database
# location is stable regardless of where the process is launched from.
_DEFAULT_PERSIST_DIRECTORY = Path(__file__).resolve().parent.parent / "chroma_db"
_DEFAULT_COLLECTION_NAME = "aras_knowledge_base"


class VectorStoreManager:
    """Creates, persists, and reloads the ARAS knowledge base's vector store.

    This class holds no document-loading, splitting, or retrieval
    logic. It is a pure storage layer: embedded document chunks in ->
    a queryable, disk-persisted `Chroma` collection out. Embedding
    itself is delegated to `EmbeddingManager` so both this class and
    a future Retriever can share the exact same embedding model
    instance and configuration.
    """

    def __init__(
        self,
        embedding_manager: Optional[EmbeddingManager] = None,
        persist_directory: Path = _DEFAULT_PERSIST_DIRECTORY,
        collection_name: str = _DEFAULT_COLLECTION_NAME,
    ) -> None:
        """Configure the vector store manager.

        Args:
            embedding_manager: The embedding manager to use for
                turning document text into vectors. A new
                `EmbeddingManager` (default model) is created if omitted.
            persist_directory: Filesystem directory the Chroma
                collection is persisted to, and reloaded from on
                subsequent executions.
            collection_name: Name of the Chroma collection holding the
                ARAS knowledge base.
        """
        self._embedding_manager = embedding_manager or EmbeddingManager()
        self._persist_directory = Path(persist_directory)
        self._collection_name = collection_name

    @property
    def persist_directory(self) -> Path:
        """The filesystem directory this vector store is persisted to."""
        return self._persist_directory

    # ------------------------------------------------------------------
    # Creation
    # ------------------------------------------------------------------

    def create_vector_store(self, documents: list[Document]) -> Chroma:
        """Embed `documents` and persist them as a new Chroma collection.

        Args:
            documents: Document chunks produced by
                `KnowledgeIngestion.split_documents` (or `.ingest`),
                with `category`/`criterion`/`section`/`source`/
                `chunk_id` metadata.

        Returns:
            The `Chroma` vector store, backed by the persisted collection.
        """
        self._persist_directory.mkdir(parents=True, exist_ok=True)
        embeddings_model = self._embedding_manager.create_embeddings_model()

        return Chroma.from_documents(
            documents=documents,
            embedding=embeddings_model,
            collection_name=self._collection_name,
            persist_directory=str(self._persist_directory),
        )

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load_vector_store(self) -> Optional[Chroma]:
        """Load the existing persisted Chroma collection, if any.

        Returns:
            The `Chroma` vector store backed by the existing on-disk
            collection, or `None` if no persisted collection exists yet
            at `persist_directory`.
        """
        if not self.vector_store_exists():
            return None

        embeddings_model = self._embedding_manager.create_embeddings_model()
        return Chroma(
            collection_name=self._collection_name,
            embedding_function=embeddings_model,
            persist_directory=str(self._persist_directory),
        )

    def vector_store_exists(self) -> bool:
        """Check whether a persisted Chroma collection already exists on disk.

        Returns:
            `True` if `persist_directory` exists and contains data
            (Chroma's SQLite backend file), `False` otherwise.
        """
        return self._persist_directory.exists() and any(self._persist_directory.iterdir())

    # ------------------------------------------------------------------
    # Combined entry point
    # ------------------------------------------------------------------

    def get_or_create_vector_store(self, documents: list[Document]) -> Chroma:
        """Load the persisted vector store, or create it if it does not exist yet.

        This is the method most callers should use: it avoids
        recomputing embeddings on every execution by reusing whatever
        was already persisted to disk, and only falls back to
        `create_vector_store` the first time the collection does not
        exist yet.

        Args:
            documents: Document chunks to embed and persist if no
                vector store already exists on disk. Ignored if a
                vector store is successfully loaded from disk.

        Returns:
            The `Chroma` vector store, either freshly created or
            reloaded from `persist_directory`.
        """
        existing_store = self.load_vector_store()
        if existing_store is not None:
            return existing_store
        return self.create_vector_store(documents)

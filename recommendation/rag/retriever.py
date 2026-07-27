"""Semantic retrieval for the ARAS Recommendation Agent's RAG stack.

This module is the fourth stage of the Retrieval-Augmented Generation
pipeline: given a natural-language query describing a detected
readiness gap (e.g. "Missing Content Security Policy header"), it
searches the already-persisted ChromaDB vector store and returns the
most semantically relevant knowledge chunks.

This module MUST NOT:
    - generate recommendations
    - call any LLM
    - modify documents
    - create embeddings manually (embedding is delegated to
      `EmbeddingManager` via `VectorStoreManager`)
    - perform document ingestion

Those responsibilities belong to other RAG components (ingestion,
embeddings, vector storage, generation) built around this one.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from langchain_chroma import Chroma
from langchain_core.documents import Document

from recommendation.rag.vector_store import VectorStoreManager

_DEFAULT_K = 5


class KnowledgeRetriever:
    """Retrieves the most relevant ARAS knowledge chunks for a query.

    This class holds no ingestion, embedding, or vector-storage
    creation logic of its own — it delegates to `VectorStoreManager`
    to load the already-persisted ChromaDB collection (built earlier
    in the pipeline), and only adds the query-time similarity search
    behavior on top of it.
    """

    def __init__(self) -> None:
        """Construct an uninitialized retriever.

        `initialize()` must be called before `retrieve()` can be used;
        this keeps constructing an instance cheap (no disk or model
        loading) and makes the loading step explicit and testable.
        """
        self._vector_store: Optional[Chroma] = None

    def initialize(self, vector_store_path: str) -> None:
        """Load the existing ChromaDB collection and its embedding model.

        Args:
            vector_store_path: Filesystem directory a `VectorStoreManager`
                has already persisted a Chroma collection to (e.g. via
                `VectorStoreManager.create_vector_store`).

        Raises:
            FileNotFoundError: If no persisted vector store exists yet
                at `vector_store_path`. The retriever only loads an
                existing collection; it does not embed or ingest
                documents itself.
        """
        vector_store_manager = VectorStoreManager(persist_directory=Path(vector_store_path))
        vector_store = vector_store_manager.load_vector_store()

        if vector_store is None:
            raise FileNotFoundError(
                f"No vector store found at '{vector_store_path}'. "
                "Run the ingestion and vector store creation steps first."
            )

        self._vector_store = vector_store

    @property
    def is_initialized(self) -> bool:
        """Whether `initialize()` has successfully loaded a vector store."""
        return self._vector_store is not None

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def retrieve(
        self,
        query: str,
        k: int = _DEFAULT_K,
        filter: Optional[dict[str, Any]] = None,
    ) -> list[Document]:
        """Retrieve the top-k most semantically relevant knowledge chunks.

        Embeds `query` with the same embedding model used to build the
        vector store, then performs a similarity search against
        ChromaDB. Every returned `Document` preserves its original
        `page_content` and `metadata` (`category`, `topic`, `source`,
        `chunk_id`) unchanged.

        Args:
            query: A natural-language description of the readiness gap
                or topic to find documentation for (e.g. "Missing
                Content Security Policy header").
            k: Maximum number of chunks to return.
            filter: Optional ChromaDB metadata filter (e.g.
                `{"category": "security"}`) restricting the search to
                chunks matching the given metadata. When omitted, the
                search runs over the entire knowledge base.

        Returns:
            The top-k most relevant `Document` chunks, ranked by
            similarity to `query`, most relevant first.
        """
        vector_store = self._require_vector_store()
        return vector_store.similarity_search(query, k=k, filter=filter)

    def retrieve_with_scores(
        self,
        query: str,
        k: int = _DEFAULT_K,
        filter: Optional[dict[str, Any]] = None,
    ) -> list[tuple[Document, float]]:
        """Retrieve the top-k most relevant chunks alongside their distance score.

        Identical to `retrieve`, but also returns each chunk's
        similarity distance so callers (e.g. debugging or reporting
        tools) can inspect how confidently a chunk matched the query.
        Lower scores indicate a closer semantic match, since ChromaDB
        reports distance rather than a normalized similarity.

        Args:
            query: The natural-language query to search for.
            k: Maximum number of chunks to return.
            filter: Optional ChromaDB metadata filter, as in `retrieve`.

        Returns:
            The top-k `(Document, distance_score)` pairs, most relevant
            (lowest distance) first.
        """
        vector_store = self._require_vector_store()
        return vector_store.similarity_search_with_score(query, k=k, filter=filter)

    def _require_vector_store(self) -> Chroma:
        """Return the loaded vector store, or raise if not yet initialized.

        Returns:
            The `Chroma` vector store loaded by `initialize`.

        Raises:
            RuntimeError: If `initialize()` has not been called yet.
        """
        if self._vector_store is None:
            raise RuntimeError(
                "KnowledgeRetriever is not initialized. Call initialize() first."
            )
        return self._vector_store

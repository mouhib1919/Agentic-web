"""Embedding generation for the ARAS Recommendation Agent's RAG stack.

This module is the second stage of the Retrieval-Augmented Generation
pipeline: it turns the chunked `Document` objects produced by
`recommendation.rag.ingestion` into numerical vector representations,
using a free, locally-run HuggingFace sentence-embedding model.

This module MUST NOT:
    - load or split documents
    - store or query a vector database
    - retrieve documents
    - call any LLM
    - generate recommendations

Those responsibilities belong to other RAG components (ingestion,
vector storage, retriever, generation) built around this one.
"""

from __future__ import annotations

from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings

# A small, free, locally-run sentence-embedding model. No API key or
# network access is required after the first download, since
# HuggingFace caches model weights locally.
_DEFAULT_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


class EmbeddingManager:
    """Creates and applies the embedding model used across the RAG pipeline.

    This class holds no document-loading, vector-storage, or retrieval
    logic. It is a pure transformation step: text in, numerical
    vectors out. `VectorStoreManager` depends on it to embed document
    chunks before writing them to ChromaDB, and later, the Retriever
    will depend on it to embed a query with the exact same model so
    query and document vectors live in the same embedding space.
    """

    def __init__(self, model_name: str = _DEFAULT_MODEL_NAME) -> None:
        """Configure the embedding manager with a specific model name.

        The underlying model is not loaded until `create_embeddings_model`
        is called, so constructing an `EmbeddingManager` has no cost
        beyond storing the model name.

        Args:
            model_name: HuggingFace Hub identifier of the
                sentence-embedding model to use.
        """
        self._model_name = model_name
        self._embeddings_model: HuggingFaceEmbeddings | None = None

    def create_embeddings_model(self) -> HuggingFaceEmbeddings:
        """Load (or reuse) the HuggingFace embedding model.

        The model is loaded lazily and cached on the instance, so
        repeated calls do not reload it from disk.

        Returns:
            A `HuggingFaceEmbeddings` instance backed by
            `sentence-transformers/all-MiniLM-L6-v2` (or whichever
            model name this manager was configured with).
        """
        if self._embeddings_model is None:
            self._embeddings_model = HuggingFaceEmbeddings(model_name=self._model_name)
        return self._embeddings_model

    def embed_documents(self, documents: list[Document]) -> list[list[float]]:
        """Embed a batch of document chunks into numerical vectors.

        Args:
            documents: Document chunks produced by
                `KnowledgeIngestion.split_documents` (or `.ingest`).

        Returns:
            One embedding vector per input document, in the same order.
        """
        embeddings_model = self.create_embeddings_model()
        texts = [document.page_content for document in documents]
        return embeddings_model.embed_documents(texts)

"""Embedding generation for the ARAS Recommendation Agent's RAG stack.

This module is the second stage of the Retrieval-Augmented Generation
pipeline: it turns text — either raw strings or the chunked `Document`
objects produced by `recommendation.rag.ingestion` — into numerical
vector representations, using a free, locally-run HuggingFace
sentence-embedding model.

This module MUST NOT:
    - load or split documents
    - store or query a vector database
    - retrieve documents
    - call any LLM
    - generate recommendations
    - modify a `Document`'s `page_content` or `metadata`

Those responsibilities belong to other RAG components (ingestion,
vector storage, retriever, generation) built around this one.
"""

from __future__ import annotations

from typing import Optional, Union

from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings

# A small, free, locally-run sentence-embedding model. No API key or
# network access is required after the first download, since
# HuggingFace caches model weights locally. Centralized here as the
# single place a future model swap (a larger model, a multilingual
# model, a domain-specific fine-tune) needs to change — every other
# RAG component depends only on `EmbeddingManager`'s public interface,
# never on this constant directly.
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


class EmbeddingManager:
    """Creates and applies the embedding model used across the RAG pipeline.

    This class holds no document-loading, splitting, vector-storage,
    or retrieval logic. It is a pure transformation step: text in,
    numerical vectors out. `VectorStoreManager` depends on it to embed
    document chunks before writing them to ChromaDB, and the Retriever
    depends on it to embed a query with the exact same model so query
    and document vectors live in the same embedding space.
    """

    def __init__(self, model_name: str = MODEL_NAME) -> None:
        """Configure the embedding manager with a specific model name.

        The underlying model is not loaded until it is first needed
        (via `embeddings`, `embed_documents`, `embed_query`, or the
        legacy `create_embeddings_model`), so constructing an
        `EmbeddingManager` has no cost beyond storing the model name —
        this keeps any module that merely imports or instantiates this
        class cheap to load, deferring the expensive `torch`/
        `sentence-transformers` initialization to first actual use.

        Args:
            model_name: HuggingFace Hub identifier of the
                sentence-embedding model to use. Swapping in a larger,
                multilingual, or domain-specific model requires only
                passing a different `model_name` here (or changing the
                `MODEL_NAME` module constant) — no other RAG component
                needs to change.
        """
        self._model_name = model_name
        self._embeddings: Optional[HuggingFaceEmbeddings] = None

    @property
    def embeddings(self) -> HuggingFaceEmbeddings:
        """The underlying LangChain embeddings object, loaded lazily.

        Directly compatible with `Chroma.from_documents(documents,
        embedding_manager.embeddings)` and
        `Chroma(embedding_function=embedding_manager.embeddings)`.

        Returns:
            A `HuggingFaceEmbeddings` instance backed by `MODEL_NAME`
            (or whichever model name this manager was configured with).

        Raises:
            RuntimeError: If the model fails to load (e.g. the model
                name is invalid, or required weights cannot be
                downloaded/read from the local cache).
        """
        if self._embeddings is None:
            try:
                self._embeddings = HuggingFaceEmbeddings(model_name=self._model_name)
            except Exception as exc:  # noqa: BLE001 - normalize into one clear, catchable error
                raise RuntimeError(
                    f"Failed to load embedding model '{self._model_name}': {exc}"
                ) from exc
        return self._embeddings

    def create_embeddings_model(self) -> HuggingFaceEmbeddings:
        """Load (or reuse) the HuggingFace embedding model.

        Kept as an alias of the `embeddings` property for backward
        compatibility with existing callers (`VectorStoreManager`).
        Prefer `embeddings` in new code.

        Returns:
            The same `HuggingFaceEmbeddings` instance as `embeddings`.
        """
        return self.embeddings

    # ------------------------------------------------------------------
    # Document embedding
    # ------------------------------------------------------------------

    def embed_documents(self, documents: Union[list[str], list[Document]]) -> list[list[float]]:
        """Embed a batch of texts or document chunks into numerical vectors.

        Never modifies its input: `Document.page_content`/`metadata`
        are read only, not written to.

        Args:
            documents: Either a list of raw strings, or a list of
                `Document` chunks (e.g. produced by
                `KnowledgeIngestion.split_documents`/`.ingest`) — the
                two forms may not be mixed within a single call.

        Returns:
            One embedding vector per input item, in the same order,
            e.g. `[[0.23, 0.12, ...], [0.45, 0.67, ...]]`.

        Raises:
            ValueError: If `documents` is empty.
            TypeError: If `documents` is not a list, or contains
                elements that are neither `str` nor `Document`.
            RuntimeError: If the embedding model fails to load or the
                underlying embedding call fails.
        """
        texts = self._extract_texts(documents)

        try:
            return self.embeddings.embed_documents(texts)
        except Exception as exc:  # noqa: BLE001 - normalize into one clear, catchable error
            raise RuntimeError(f"Failed to embed {len(texts)} document(s): {exc}") from exc

    @staticmethod
    def _extract_texts(documents: Union[list[str], list[Document]]) -> list[str]:
        """Validate and normalize `embed_documents` input into plain text.

        Args:
            documents: The raw `embed_documents` argument.

        Returns:
            One string per input item, preserving order.

        Raises:
            ValueError: If `documents` is empty.
            TypeError: If `documents` is not a list, or contains
                elements that are neither `str` nor `Document`.
        """
        if not isinstance(documents, list):
            raise TypeError(f"embed_documents expects a list, got {type(documents).__name__}.")
        if not documents:
            raise ValueError("Cannot embed an empty list of documents.")

        texts: list[str] = []
        for index, item in enumerate(documents):
            if isinstance(item, Document):
                texts.append(item.page_content)
            elif isinstance(item, str):
                texts.append(item)
            else:
                raise TypeError(
                    f"embed_documents expects list[str] or list[Document]; "
                    f"element {index} has type {type(item).__name__}."
                )
        return texts

    # ------------------------------------------------------------------
    # Query embedding
    # ------------------------------------------------------------------

    def embed_query(self, query: str) -> list[float]:
        """Embed a single query string, for use by the Retriever.

        Uses the same model and configuration as `embed_documents`, so
        the resulting vector lives in the same embedding space as
        vectors already stored in ChromaDB.

        Args:
            query: The natural-language query to embed.

        Returns:
            The query's embedding vector.

        Raises:
            TypeError: If `query` is not a string.
            ValueError: If `query` is empty or whitespace-only.
            RuntimeError: If the embedding model fails to load or the
                underlying embedding call fails.
        """
        if not isinstance(query, str):
            raise TypeError(f"embed_query expects a string, got {type(query).__name__}.")
        if not query.strip():
            raise ValueError("Cannot embed an empty query string.")

        try:
            return self.embeddings.embed_query(query)
        except Exception as exc:  # noqa: BLE001 - normalize into one clear, catchable error
            raise RuntimeError(f"Failed to embed query: {exc}") from exc

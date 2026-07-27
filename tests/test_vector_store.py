"""Tests for :class:`EmbeddingManager` and :class:`VectorStoreManager`.

Covers, against the real ARAS knowledge base ingested by
`KnowledgeIngestion`: embedding model initialization, embedding
document chunks, creating a persisted ChromaDB vector store, and
reloading it without recomputing embeddings. No retriever or LLM is
exercised by these tests — only embedding generation and vector
storage.

Requires network access on first run to download the
`sentence-transformers/all-MiniLM-L6-v2` model weights from the
HuggingFace Hub; subsequent runs use the local HuggingFace cache.

Each test that creates a Chroma collection uses its own temporary
persist directory (rather than sharing one), since ChromaDB's SQLite
backend can keep file handles open past the end of a test on Windows,
which would make `shutil.rmtree` cleanup between shared-directory
tests unreliable.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

# Allow running this file directly (e.g. from an IDE "Run" button) by
# ensuring the project root is importable, not just the `tests/` folder.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings

from recommendation.rag.embeddings import EmbeddingManager
from recommendation.rag.ingestion import KnowledgeIngestion
from recommendation.rag.vector_store import VectorStoreManager

KNOWLEDGE_PATH = str(Path(__file__).resolve().parent.parent / "recommendation" / "knowledge")


def _load_chunks() -> list[Document]:
    """Run the already-tested ingestion pipeline to get real document chunks."""
    return KnowledgeIngestion().ingest(KNOWLEDGE_PATH)


def _temp_persist_directory() -> Path:
    """Create a fresh, isolated persist directory for a single test."""
    return Path(tempfile.mkdtemp(prefix="aras_chroma_test_"))


def test_embedding_model_initializes_successfully() -> None:
    """Scenario 1: the embedding model loads successfully."""
    manager = EmbeddingManager()

    model = manager.create_embeddings_model()
    print(f"embedding model: {type(model).__name__}")

    assert isinstance(model, HuggingFaceEmbeddings)

    # Loading a second time reuses the cached instance rather than reloading.
    assert manager.create_embeddings_model() is model


def test_embed_documents_from_ingestion_output() -> None:
    """Scenario 2: embedding the 43 ingested chunks produces one vector each."""
    chunks = _load_chunks()
    print(f"Number of documents to embed: {len(chunks)}")

    manager = EmbeddingManager()
    vectors = manager.embed_documents(chunks)

    assert len(vectors) == len(chunks)
    assert len(chunks) > 0
    assert all(isinstance(vector, list) for vector in vectors)
    assert all(len(vector) == len(vectors[0]) for vector in vectors)
    print(f"Embedding dimensionality: {len(vectors[0])}")


def test_create_vector_store_persists_documents_and_metadata() -> None:
    """Scenario 3: creating the Chroma vector store persists data + metadata."""
    chunks = _load_chunks()
    persist_directory = _temp_persist_directory()
    manager = VectorStoreManager(persist_directory=persist_directory)

    try:
        assert manager.vector_store_exists() is False

        store = manager.create_vector_store(chunks)

        print(f"Vector store location: {manager.persist_directory}")
        assert isinstance(store, Chroma)
        assert manager.persist_directory.exists()
        assert manager.vector_store_exists() is True

        # Documents are actually stored (not just an empty collection).
        assert store._collection.count() == len(chunks)

        # Metadata survives the round trip through embedding + storage, and
        # is usable for similarity search filtering by a future retriever.
        csp_results = store.similarity_search(
            "Content Security Policy header for XSS mitigation", k=1
        )
        assert len(csp_results) == 1
        result_metadata = csp_results[0].metadata
        print(f"Example stored metadata: {result_metadata}")
        assert {"category", "topic", "source", "chunk_id"} <= result_metadata.keys()
    finally:
        shutil.rmtree(persist_directory, ignore_errors=True)


def test_load_vector_store_reuses_persisted_embeddings() -> None:
    """Scenario 4: an existing ChromaDB collection can be reloaded without
    recomputing embeddings.
    """
    chunks = _load_chunks()
    persist_directory = _temp_persist_directory()

    try:
        creating_manager = VectorStoreManager(persist_directory=persist_directory)
        assert creating_manager.load_vector_store() is None

        creating_manager.create_vector_store(chunks)

        # A brand-new manager instance (fresh EmbeddingManager, no in-memory
        # state) reloads the same persisted collection from disk.
        reloading_manager = VectorStoreManager(persist_directory=persist_directory)
        reloaded_store = reloading_manager.load_vector_store()

        assert reloaded_store is not None
        assert isinstance(reloaded_store, Chroma)
        assert reloaded_store._collection.count() == len(chunks)

        results = reloaded_store.similarity_search("robots.txt crawler discovery", k=2)
        assert len(results) == 2
        for result in results:
            assert {"category", "topic", "source", "chunk_id"} <= result.metadata.keys()
    finally:
        shutil.rmtree(persist_directory, ignore_errors=True)


def test_get_or_create_vector_store_avoids_recreation_when_present() -> None:
    """`get_or_create_vector_store` creates once, then reuses on later calls."""
    chunks = _load_chunks()
    persist_directory = _temp_persist_directory()

    try:
        manager = VectorStoreManager(persist_directory=persist_directory)

        first_store = manager.get_or_create_vector_store(chunks)
        assert first_store._collection.count() == len(chunks)

        # Calling again with a fresh manager instance must load, not recreate.
        second_manager = VectorStoreManager(persist_directory=persist_directory)
        second_store = second_manager.get_or_create_vector_store(chunks)
        assert second_store._collection.count() == len(chunks)
    finally:
        shutil.rmtree(persist_directory, ignore_errors=True)


if __name__ == "__main__":
    test_embedding_model_initializes_successfully()
    test_embed_documents_from_ingestion_output()
    test_create_vector_store_persists_documents_and_metadata()
    test_load_vector_store_reuses_persisted_embeddings()
    test_get_or_create_vector_store_avoids_recreation_when_present()
    print("All tests passed.")

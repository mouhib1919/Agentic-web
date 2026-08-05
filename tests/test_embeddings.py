"""Unit tests for :class:`EmbeddingManager` (refined embedding layer).

Covers model loading, single-query embedding, document (chunk)
embedding, error handling for invalid/empty input, and compatibility
with `Chroma.from_documents`. Uses real ARAS knowledge chunks (via the
already-tested `KnowledgeIngestion`) rather than synthetic data where
representative. No retriever, LLM, or recommendation-generation logic
is exercised by these tests.

Requires network access on first run to download the
`sentence-transformers/all-MiniLM-L6-v2` model weights; subsequent
runs use the local HuggingFace cache.
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

from recommendation.rag.embeddings import MODEL_NAME, EmbeddingManager

_EMBEDDING_DIMENSIONS = 384


def test_model_loading() -> None:
    """Test 1: the embedding model loads successfully."""
    manager = EmbeddingManager()

    model = manager.embeddings

    print("Embedding model loaded successfully")
    print(f"model: {type(model).__name__}, name: {MODEL_NAME}")

    assert isinstance(model, HuggingFaceEmbeddings)
    # Lazily loaded once, then cached: repeated access returns the same instance.
    assert manager.embeddings is model
    # The legacy alias returns the exact same underlying model.
    assert manager.create_embeddings_model() is model


def test_single_query_embedding() -> None:
    """Test 2: a single query embeds to a 384-dimensional vector."""
    manager = EmbeddingManager()

    vector = manager.embed_query("How to fix missing CSP header?")

    print(f"query vector dimension: {len(vector)}")

    assert isinstance(vector, list)
    assert len(vector) == _EMBEDDING_DIMENSIONS
    assert all(isinstance(value, float) for value in vector)


def test_document_embedding_from_aras_chunks() -> None:
    """Test 3: three ARAS-style chunks embed to three 384-dim vectors."""
    manager = EmbeddingManager()
    chunks = [
        Document(
            page_content="CSP recommendation",
            metadata={"category": "security", "criterion": "csp"},
        ),
        Document(
            page_content="OpenAPI documentation",
            metadata={"category": "interaction", "criterion": "api_documentation"},
        ),
        Document(
            page_content="Robots.txt optimization",
            metadata={"category": "discoverability", "criterion": "robots_txt"},
        ),
    ]
    original_metadata = [dict(chunk.metadata) for chunk in chunks]
    original_content = [chunk.page_content for chunk in chunks]

    vectors = manager.embed_documents(chunks)

    print(f"embedded {len(vectors)} document(s), dimension {len(vectors[0])}")

    assert len(vectors) == 3
    assert all(len(vector) == _EMBEDDING_DIMENSIONS for vector in vectors)

    # embed_documents must never mutate page_content or metadata.
    assert [chunk.page_content for chunk in chunks] == original_content
    assert [chunk.metadata for chunk in chunks] == original_metadata


def test_document_embedding_accepts_plain_strings() -> None:
    """embed_documents also accepts list[str], not only list[Document]."""
    manager = EmbeddingManager()

    vectors = manager.embed_documents(["first chunk", "second chunk"])

    assert len(vectors) == 2
    assert all(len(vector) == _EMBEDDING_DIMENSIONS for vector in vectors)


def test_embed_documents_rejects_empty_input() -> None:
    """Error handling: an empty document list raises a clear ValueError."""
    manager = EmbeddingManager()

    try:
        manager.embed_documents([])
        assert False, "expected ValueError for empty input"
    except ValueError as error:
        print(f"expected error: {error}")


def test_embed_documents_rejects_invalid_element_types() -> None:
    """Error handling: non-str/Document elements raise a clear TypeError."""
    manager = EmbeddingManager()

    try:
        manager.embed_documents([123, 456])  # type: ignore[list-item]
        assert False, "expected TypeError for invalid element type"
    except TypeError as error:
        print(f"expected error: {error}")


def test_embed_documents_rejects_non_list_input() -> None:
    """Error handling: a non-list argument raises a clear TypeError."""
    manager = EmbeddingManager()

    try:
        manager.embed_documents("not a list")  # type: ignore[arg-type]
        assert False, "expected TypeError for non-list input"
    except TypeError as error:
        print(f"expected error: {error}")


def test_embed_query_rejects_empty_string() -> None:
    """Error handling: an empty/whitespace query raises a clear ValueError."""
    manager = EmbeddingManager()

    try:
        manager.embed_query("   ")
        assert False, "expected ValueError for empty query"
    except ValueError as error:
        print(f"expected error: {error}")


def test_embed_query_rejects_non_string_input() -> None:
    """Error handling: a non-string query raises a clear TypeError."""
    manager = EmbeddingManager()

    try:
        manager.embed_query(42)  # type: ignore[arg-type]
        assert False, "expected TypeError for non-string query"
    except TypeError as error:
        print(f"expected error: {error}")


def test_model_loading_failure_raises_runtime_error() -> None:
    """Error handling: a bad model name surfaces as a clear RuntimeError."""
    manager = EmbeddingManager(model_name="this-model-does-not-exist/invalid-12345")

    try:
        manager.embeddings
        assert False, "expected RuntimeError for a nonexistent model"
    except RuntimeError as error:
        print(f"expected error: {error}")


def test_chroma_compatibility() -> None:
    """Test 4: Chroma.from_documents works with embedding_manager.embeddings."""
    manager = EmbeddingManager()
    documents = [
        Document(
            page_content="Missing Content Security Policy leaves a site open to XSS.",
            metadata={"category": "security", "criterion": "csp"},
        ),
        Document(
            page_content="Publish an OpenAPI document to describe available endpoints.",
            metadata={"category": "interaction", "criterion": "api_documentation"},
        ),
    ]

    persist_directory = Path(tempfile.mkdtemp(prefix="aras_embeddings_chroma_test_"))
    try:
        store = Chroma.from_documents(
            documents,
            manager.embeddings,
            persist_directory=str(persist_directory),
        )
        print(f"Chroma collection count: {store._collection.count()}")

        assert store._collection.count() == 2

        results = store.similarity_search("How do I configure CSP?", k=1)
        print(f"retrieved: {[r.metadata for r in results]}")
        assert results[0].metadata["criterion"] == "csp"
    finally:
        shutil.rmtree(persist_directory, ignore_errors=True)


if __name__ == "__main__":
    test_model_loading()
    test_single_query_embedding()
    test_document_embedding_from_aras_chunks()
    test_document_embedding_accepts_plain_strings()
    test_embed_documents_rejects_empty_input()
    test_embed_documents_rejects_invalid_element_types()
    test_embed_documents_rejects_non_list_input()
    test_embed_query_rejects_empty_string()
    test_embed_query_rejects_non_string_input()
    test_model_loading_failure_raises_runtime_error()
    test_chroma_compatibility()
    print("All tests passed.")

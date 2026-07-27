"""Tests for :class:`KnowledgeRetriever`.

Covers, against the real ARAS knowledge base and its persisted
ChromaDB collection (built by `KnowledgeIngestion` +
`VectorStoreManager`): retriever initialization, semantic similarity
search for security and interaction queries, and metadata-filtered
search. No LLM or recommendation-generation logic is exercised by
these tests — only retrieval.

Requires network access on first run to download the
`sentence-transformers/all-MiniLM-L6-v2` model weights (shared with
`test_vector_store.py`); subsequent runs use the local HuggingFace cache.

Each test builds its own isolated, disposable vector store (via
`VectorStoreManager` + `KnowledgeIngestion`) rather than depending on
`recommendation/chroma_db/` already existing on disk, so this suite
runs standalone regardless of execution order relative to
`test_vector_store.py`.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

# Allow running this file directly (e.g. from an IDE "Run" button) by
# ensuring the project root is importable, not just the `tests/` folder.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_core.documents import Document

from recommendation.rag.ingestion import KnowledgeIngestion
from recommendation.rag.retriever import KnowledgeRetriever
from recommendation.rag.vector_store import VectorStoreManager

KNOWLEDGE_PATH = str(Path(__file__).resolve().parent.parent / "recommendation" / "knowledge")


def _build_test_vector_store() -> Path:
    """Ingest the real knowledge base into a fresh, isolated Chroma collection.

    Returns:
        The temporary persist directory the collection was written to.
        Callers are responsible for removing it once done.
    """
    persist_directory = Path(tempfile.mkdtemp(prefix="aras_retriever_test_"))
    chunks = KnowledgeIngestion().ingest(KNOWLEDGE_PATH)
    VectorStoreManager(persist_directory=persist_directory).create_vector_store(chunks)
    return persist_directory


def _print_retrieved_documents(query: str, documents: list[Document]) -> None:
    print(f'Query: "{query}"')
    print("Retrieved documents:")
    for index, document in enumerate(documents, start=1):
        print(f"Document {index}:")
        print(f"  metadata: {document.metadata}")
    print()


def _print_retrieved_documents_with_scores(
    query: str, results: list[tuple[Document, float]]
) -> None:
    print(f'Query: "{query}"')
    print("Retrieved documents:")
    for index, (document, score) in enumerate(results, start=1):
        print(f"Document {index}:")
        print(f"  metadata: {document.metadata}")
        print(f"  similarity score (distance): {score}")
    print()


def test_initialize_loads_vector_store_and_embedding_model() -> None:
    """Test 1: initializing the retriever loads ChromaDB and the embedding model."""
    persist_directory = _build_test_vector_store()

    try:
        retriever = KnowledgeRetriever()
        assert retriever.is_initialized is False

        retriever.initialize(str(persist_directory))

        assert retriever.is_initialized is True
    finally:
        shutil.rmtree(persist_directory, ignore_errors=True)


def test_initialize_raises_when_no_vector_store_exists() -> None:
    """`initialize` must fail clearly rather than silently create an empty store."""
    empty_directory = Path(tempfile.mkdtemp(prefix="aras_retriever_empty_"))

    try:
        retriever = KnowledgeRetriever()
        try:
            retriever.initialize(str(empty_directory))
            assert False, "expected FileNotFoundError"
        except FileNotFoundError:
            pass
        assert retriever.is_initialized is False
    finally:
        shutil.rmtree(empty_directory, ignore_errors=True)


def test_retrieve_finds_csp_documentation_for_security_query() -> None:
    """Test 2: a CSP-related query retrieves the security/csp document."""
    persist_directory = _build_test_vector_store()

    try:
        retriever = KnowledgeRetriever()
        retriever.initialize(str(persist_directory))

        query = "Content Security Policy missing"
        results = retriever.retrieve_with_scores(query, k=5)
        _print_retrieved_documents_with_scores(query, results)

        documents = [document for document, _ in results]
        assert len(documents) == 5
        assert all(isinstance(document, Document) for document in documents)
        assert any(document.metadata["category"] == "security" for document in documents)
        assert any(document.metadata["topic"] == "csp" for document in documents)
    finally:
        shutil.rmtree(persist_directory, ignore_errors=True)


def test_retrieve_finds_interaction_documentation_for_api_query() -> None:
    """Test 3: an API-exposure query retrieves interaction/openapi or graphql."""
    persist_directory = _build_test_vector_store()

    try:
        retriever = KnowledgeRetriever()
        retriever.initialize(str(persist_directory))

        query = "How to expose APIs for AI agents"
        documents = retriever.retrieve(query, k=5)
        _print_retrieved_documents(query, documents)

        assert len(documents) == 5
        assert any(document.metadata["category"] == "interaction" for document in documents)
        assert any(
            document.metadata["topic"] in {"openapi", "graphql"} for document in documents
        )
    finally:
        shutil.rmtree(persist_directory, ignore_errors=True)


def test_retrieve_with_metadata_filter_restricts_category() -> None:
    """Test 4: filtering by category="security" returns only security chunks."""
    persist_directory = _build_test_vector_store()

    try:
        retriever = KnowledgeRetriever()
        retriever.initialize(str(persist_directory))

        query = "security headers"
        documents = retriever.retrieve(query, k=5, filter={"category": "security"})
        _print_retrieved_documents(query, documents)

        assert len(documents) > 0
        assert all(document.metadata["category"] == "security" for document in documents)
    finally:
        shutil.rmtree(persist_directory, ignore_errors=True)


def test_retrieve_without_filter_can_span_multiple_categories() -> None:
    """Without a filter, results are not restricted to a single category."""
    persist_directory = _build_test_vector_store()

    try:
        retriever = KnowledgeRetriever()
        retriever.initialize(str(persist_directory))

        documents = retriever.retrieve("website technical best practices", k=10)

        categories_found = {document.metadata["category"] for document in documents}
        assert len(categories_found) >= 2
    finally:
        shutil.rmtree(persist_directory, ignore_errors=True)


if __name__ == "__main__":
    test_initialize_loads_vector_store_and_embedding_model()
    test_initialize_raises_when_no_vector_store_exists()
    test_retrieve_finds_csp_documentation_for_security_query()
    test_retrieve_finds_interaction_documentation_for_api_query()
    test_retrieve_with_metadata_filter_restricts_category()
    test_retrieve_without_filter_can_span_multiple_categories()
    print("All tests passed.")

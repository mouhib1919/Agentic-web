"""Unit tests for :class:`ARASRetriever` (metadata filter + bi-encoder + re-ranker).

Builds a temporary ChromaDB collection from the real
`knowledge/aras_knowledge/` base (via the already-tested
`KnowledgeIngestion` and `VectorStoreManager`) once per test run, then
exercises `ARASRetriever.retrieve()` against real recommendation
contexts. No LLM or recommendation-generation logic is exercised by
these tests.

Requires network access on first run to download the
`sentence-transformers/all-MiniLM-L6-v2` embedding model and the
`cross-encoder/ms-marco-MiniLM-L-6-v2` re-ranking model; subsequent
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

from recommendation.rag.ingestion import KnowledgeIngestion
from recommendation.rag.retriever import ARASRetriever, KnowledgeRetriever
from recommendation.rag.vector_store import VectorStoreManager

KNOWLEDGE_PATH = str(Path(__file__).resolve().parent.parent / "knowledge" / "aras_knowledge")

_PERSIST_DIRECTORY = Path(tempfile.mkdtemp(prefix="aras_retriever_test_"))


def _build_retriever() -> ARASRetriever:
    """Construct an `ARASRetriever` backed by the shared test vector store."""
    retriever = ARASRetriever(knowledge_retriever=KnowledgeRetriever())
    retriever.initialize(str(_PERSIST_DIRECTORY))
    return retriever


def setup_module(_module: object) -> None:
    """Build the shared temporary vector store once, before any test runs."""
    chunks = KnowledgeIngestion().ingest(KNOWLEDGE_PATH)
    VectorStoreManager(persist_directory=_PERSIST_DIRECTORY).create_vector_store(chunks)


def teardown_module(_module: object) -> None:
    """Remove the shared temporary vector store after all tests have run."""
    shutil.rmtree(_PERSIST_DIRECTORY, ignore_errors=True)


def test_build_query_includes_dimension_criterion_issue_and_objective() -> None:
    """`build_query` produces a structured natural-language query."""
    query = ARASRetriever.build_query(
        {
            "category": "security",
            "criterion": "csp",
            "issue": "Missing CSP header",
            "priority": "HIGH",
        }
    )
    print(f"built query:\n{query}")

    assert "security" in query
    assert "csp" in query
    assert "Missing CSP header" in query
    assert "remediation" in query.lower()


def test_csp_retrieval() -> None:
    """Test 1: CSP retrieval returns csp.md chunks, not graphql.md/robots.md."""
    retriever = _build_retriever()

    results = retriever.retrieve(
        {"category": "security", "criterion": "csp", "issue": "Missing CSP header"}
    )
    sources = [document.metadata["source"] for document in results]
    print(f"CSP retrieval sources: {sources}")

    assert results
    assert any(source.endswith("security/csp.md") for source in sources)
    assert not any(source.endswith("graphql.md") for source in sources)
    assert not any(source.endswith("robots.md") for source in sources)


def test_api_documentation_retrieval() -> None:
    """Test 2: API documentation retrieval returns interaction/api_documentation.md chunks."""
    retriever = _build_retriever()

    results = retriever.retrieve(
        {
            "category": "interaction",
            "criterion": "api_documentation",
            "issue": "Missing API documentation",
        }
    )
    sources = [document.metadata["source"] for document in results]
    print(f"API documentation retrieval sources: {sources}")

    assert results
    assert all(source.endswith("interaction/api_documentation.md") for source in sources)


def test_metadata_filtering_never_crosses_criteria() -> None:
    """Test 3: criterion=csp never retrieves criterion=graphql chunks."""
    retriever = _build_retriever()

    results = retriever.retrieve(
        {"category": "security", "criterion": "csp", "issue": "Missing CSP header"}
    )

    assert all(document.metadata["criterion"] == "csp" for document in results)


def test_unknown_criterion_returns_empty_without_raising() -> None:
    """Test 4: an unknown criterion returns [] instead of raising."""
    retriever = _build_retriever()

    results = retriever.retrieve(
        {
            "category": "security",
            "criterion": "does-not-exist",
            "issue": "Some issue with no matching knowledge",
        }
    )
    print(f"unknown criterion results: {results}")

    assert results == []


def test_uninitialized_retriever_returns_empty_without_raising() -> None:
    """An uninitialized retriever also returns [] rather than raising."""
    retriever = ARASRetriever()

    results = retriever.retrieve(
        {"category": "security", "criterion": "csp", "issue": "Missing CSP header"}
    )

    assert results == []


def test_dynamic_top_k_overrides_are_configurable() -> None:
    """Per-criterion top_k overrides are honored and can be reconfigured."""
    retriever = ARASRetriever(
        knowledge_retriever=KnowledgeRetriever(),
        top_k_overrides={("security", "csp"): 1},
    )
    retriever.initialize(str(_PERSIST_DIRECTORY))

    assert retriever._resolve_candidate_k("security", "csp") == 1
    assert retriever._resolve_candidate_k("interaction", "api_documentation") == 10


def test_returned_documents_preserve_content_and_metadata() -> None:
    """Retrieved results are plain Documents with unmodified content/metadata."""
    retriever = _build_retriever()

    results = retriever.retrieve(
        {"category": "security", "criterion": "csp", "issue": "Missing CSP header"}
    )

    assert results
    top_document = results[0]
    assert isinstance(top_document.page_content, str) and top_document.page_content.strip()
    assert {"category", "criterion", "source"} <= top_document.metadata.keys()


if __name__ == "__main__":
    setup_module(None)
    try:
        test_build_query_includes_dimension_criterion_issue_and_objective()
        test_csp_retrieval()
        test_api_documentation_retrieval()
        test_metadata_filtering_never_crosses_criteria()
        test_unknown_criterion_returns_empty_without_raising()
        test_uninitialized_retriever_returns_empty_without_raising()
        test_dynamic_top_k_overrides_are_configurable()
        test_returned_documents_preserve_content_and_metadata()
        print("All tests passed.")
    finally:
        teardown_module(None)

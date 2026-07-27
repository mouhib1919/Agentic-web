"""Unit tests for :class:`KnowledgeIngestion`.

Covers, against the real ARAS knowledge base under
`recommendation/knowledge/`: loading every Markdown document,
metadata extraction from file paths, semantic chunk splitting with
metadata preservation, and the full `ingest()` pipeline. No
embeddings, vector store, retriever, or LLM is exercised by these
tests — only document loading and splitting.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running this file directly (e.g. from an IDE "Run" button) by
# ensuring the project root is importable, not just the `tests/` folder.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_core.documents import Document

from recommendation.rag.ingestion import KnowledgeIngestion

KNOWLEDGE_PATH = str(Path(__file__).resolve().parent.parent / "recommendation" / "knowledge")

_EXPECTED_CATEGORIES = {"discoverability", "comprehension", "interaction", "security"}
_MAX_CHUNK_SIZE = 1500
# RecursiveCharacterTextSplitter's chunk_size is a soft target measured against
# its own separator-based splits, not a hard character cap, so a small
# tolerance avoids flaking on borderline chunks while still catching real
# fragmentation regressions.
_CHUNK_SIZE_TOLERANCE = 50


def _print_documents(label: str, documents: list[Document]) -> None:
    print(f"--- {label} ---")
    print(f"count: {len(documents)}")
    for document in documents[:5]:
        print(f"  {document.metadata} (len={len(document.page_content)})")
    print()


def _print_all_chunks_debug(chunks: list[Document]) -> None:
    """Temporary debug output: every chunk's metadata and content length."""
    print("=" * 40)
    print(f"Number of chunks: {len(chunks)}")
    print("=" * 40)
    for chunk in chunks:
        print(chunk.metadata)
        print(f"length={len(chunk.page_content)}")
        print()


def test_load_documents_finds_every_knowledge_file() -> None:
    """1) Loading: documents are loaded successfully."""
    ingestion = KnowledgeIngestion()

    documents = ingestion.load_documents(KNOWLEDGE_PATH)
    _print_documents("load_documents", documents)

    assert len(documents) > 0
    assert all(isinstance(document, Document) for document in documents)
    assert all(document.page_content.strip() for document in documents)

    # Every expected dimension folder is represented in the loaded set.
    categories_found = {document.metadata["category"] for document in documents}
    assert _EXPECTED_CATEGORIES <= categories_found


def test_metadata_extraction_matches_file_path() -> None:
    """Metadata is derived correctly from the directory structure."""
    ingestion = KnowledgeIngestion()

    documents = ingestion.load_documents(KNOWLEDGE_PATH)
    csp_document = next(
        document for document in documents if document.metadata["source"].endswith("csp.md")
    )

    print(f"csp.md metadata: {csp_document.metadata}")

    assert csp_document.metadata["category"] == "security"
    assert csp_document.metadata["topic"] == "csp"
    assert csp_document.metadata["source"] == "knowledge/security/csp.md"


def test_metadata_extraction_is_dynamic_across_categories() -> None:
    """Metadata extraction must not hardcode category names anywhere."""
    ingestion = KnowledgeIngestion()
    documents = ingestion.load_documents(KNOWLEDGE_PATH)

    jsonld_document = next(
        document for document in documents if document.metadata["source"].endswith("jsonld.md")
    )
    assert jsonld_document.metadata["category"] == "comprehension"
    assert jsonld_document.metadata["topic"] == "jsonld"

    openapi_document = next(
        document for document in documents if document.metadata["source"].endswith("openapi.md")
    )
    assert openapi_document.metadata["category"] == "interaction"
    assert openapi_document.metadata["topic"] == "openapi"


def test_split_documents_produces_more_chunks_than_source_files() -> None:
    """2) Splitting: the ARAS knowledge documents (600-1000 words each) are
    long enough relative to chunk_size=1500 that splitting must actually
    fragment them, so total chunk count must exceed the source file count.
    """
    ingestion = KnowledgeIngestion()
    documents = ingestion.load_documents(KNOWLEDGE_PATH)

    chunks = ingestion.split_documents(documents)
    _print_documents("split_documents", chunks)

    assert len(chunks) > len(documents)
    assert all(isinstance(chunk, Document) for chunk in chunks)


def test_split_documents_preserves_metadata() -> None:
    """3) Metadata preservation: every chunk keeps category/topic/source."""
    ingestion = KnowledgeIngestion()
    documents = ingestion.load_documents(KNOWLEDGE_PATH)
    chunks = ingestion.split_documents(documents)

    for chunk in chunks:
        assert "category" in chunk.metadata
        assert "topic" in chunk.metadata
        assert "source" in chunk.metadata
        assert "chunk_id" in chunk.metadata

    # chunk_id values for a single source document are contiguous from 0.
    csp_chunks = [chunk for chunk in chunks if chunk.metadata["topic"] == "csp"]
    assert [chunk.metadata["chunk_id"] for chunk in csp_chunks] == list(range(len(csp_chunks)))

    # A chunk's non-chunk_id metadata matches its source document's metadata.
    documents_by_source = {document.metadata["source"]: document.metadata for document in documents}
    for chunk in chunks:
        source_metadata = documents_by_source[chunk.metadata["source"]]
        assert chunk.metadata["category"] == source_metadata["category"]
        assert chunk.metadata["topic"] == source_metadata["topic"]


def test_split_documents_respects_chunk_size() -> None:
    """4) Chunk size: every chunk respects approximately <= 1500 characters."""
    ingestion = KnowledgeIngestion()
    documents = ingestion.load_documents(KNOWLEDGE_PATH)
    chunks = ingestion.split_documents(documents)

    oversized = [len(chunk.page_content) for chunk in chunks if len(chunk.page_content) > _MAX_CHUNK_SIZE]
    print(f"oversized chunk lengths: {oversized}")

    for chunk in chunks:
        assert len(chunk.page_content) <= _MAX_CHUNK_SIZE + _CHUNK_SIZE_TOLERANCE


def test_split_documents_does_not_over_split_short_documents() -> None:
    """A document shorter than chunk_size must not be split unnecessarily."""
    ingestion = KnowledgeIngestion(chunk_size=1500, chunk_overlap=200)
    short_document = Document(
        page_content="Short content well under the chunk size limit.",
        metadata={"category": "security", "topic": "example", "source": "knowledge/security/example.md"},
    )

    chunks = ingestion.split_documents([short_document])

    assert len(chunks) == 1
    assert chunks[0].page_content == short_document.page_content
    assert chunks[0].metadata["chunk_id"] == 0


def test_ingest_runs_the_full_pipeline_and_prints_debug_output() -> None:
    """Complete pipeline: `ingest()` returns chunks ready for embedding.

    Also prints the temporary debug output requested for this review:
    total chunk count, and each chunk's metadata plus content length.
    """
    ingestion = KnowledgeIngestion()

    documents = ingestion.load_documents(KNOWLEDGE_PATH)
    chunks = ingestion.ingest(KNOWLEDGE_PATH)
    _print_all_chunks_debug(chunks)

    assert len(chunks) > 0
    assert len(chunks) > len(documents)
    assert all(isinstance(chunk, Document) for chunk in chunks)
    assert all(chunk.page_content.strip() for chunk in chunks)
    assert all(
        {"category", "topic", "source", "chunk_id"} <= chunk.metadata.keys() for chunk in chunks
    )
    assert all(len(chunk.page_content) <= _MAX_CHUNK_SIZE + _CHUNK_SIZE_TOLERANCE for chunk in chunks)

    # Every knowledge file that was loaded is represented among the chunks.
    expected_sources = {document.metadata["source"] for document in documents}
    chunk_sources = {chunk.metadata["source"] for chunk in chunks}
    assert expected_sources == chunk_sources


if __name__ == "__main__":
    test_load_documents_finds_every_knowledge_file()
    test_metadata_extraction_matches_file_path()
    test_metadata_extraction_is_dynamic_across_categories()
    test_split_documents_produces_more_chunks_than_source_files()
    test_split_documents_preserves_metadata()
    test_split_documents_respects_chunk_size()
    test_split_documents_does_not_over_split_short_documents()
    test_ingest_runs_the_full_pipeline_and_prints_debug_output()
    print("All tests passed.")

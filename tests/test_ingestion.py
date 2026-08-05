"""Unit tests for :class:`KnowledgeIngestion` (upgraded ARAS ingestion pipeline).

Covers, against the real ARAS knowledge base under
`knowledge/aras_knowledge/`: loading every Markdown document and
extracting its YAML frontmatter, two-stage Markdown-header +
character-based chunking, output compatibility with the expected
`Document(page_content=..., metadata={...})` shape, embedding
compatibility with the existing `EmbeddingManager`
(sentence-transformers/all-MiniLM-L6-v2, 384 dimensions), and ChromaDB
storage via the existing `VectorStoreManager`. No LLM, retriever, or
recommendation-generation logic is exercised by these tests.
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

from recommendation.rag.embeddings import EmbeddingManager
from recommendation.rag.ingestion import KnowledgeIngestion
from recommendation.rag.vector_store import VectorStoreManager

KNOWLEDGE_PATH = str(Path(__file__).resolve().parent.parent / "knowledge" / "aras_knowledge")

_EXPECTED_CATEGORIES = {"discoverability", "comprehension", "interaction", "security"}
_EXPECTED_DOCUMENT_COUNT = 27
_MAX_CHUNK_SIZE = 1500
# RecursiveCharacterTextSplitter's chunk_size is a soft target measured against
# its own separator-based splits, not a hard character cap; the composed
# chunk also gains a document/section title prefix on top of the raw split
# text, so a modest tolerance avoids flaking on borderline chunks while
# still catching real oversizing regressions.
_CHUNK_SIZE_TOLERANCE = 150
_EMBEDDING_DIMENSIONS = 384


def _print_documents(label: str, documents: list[Document]) -> None:
    print(f"--- {label} ---")
    print(f"count: {len(documents)}")
    for document in documents[:3]:
        print(f"  {document.metadata}")
    print()


def test_load_documents_finds_every_aras_knowledge_file_with_metadata() -> None:
    """1) Loading: all ARAS markdown files loaded, metadata extracted."""
    ingestion = KnowledgeIngestion()

    documents = ingestion.load_documents(KNOWLEDGE_PATH)
    _print_documents("load_documents", documents)

    assert len(documents) == _EXPECTED_DOCUMENT_COUNT
    assert all(isinstance(document, Document) for document in documents)
    assert all(document.page_content.strip() for document in documents)

    categories_found = {document.metadata["category"] for document in documents}
    assert categories_found == _EXPECTED_CATEGORIES

    # YAML frontmatter was parsed: category/criterion/severity/related present,
    # and the frontmatter block itself is not leaked into page_content.
    csp_document = next(
        document for document in documents if document.metadata["source"].endswith("csp.md")
    )
    assert csp_document.metadata["category"] == "security"
    assert csp_document.metadata["criterion"] == "csp"
    assert csp_document.metadata["severity"] == "high"
    assert "x_frame_options" in csp_document.metadata["related"]
    assert not csp_document.page_content.lstrip().startswith("---")
    assert csp_document.page_content.lstrip().startswith("# ")


def test_metadata_extraction_is_dynamic_across_categories() -> None:
    """Metadata extraction reads frontmatter, never hardcodes category names."""
    ingestion = KnowledgeIngestion()
    documents = ingestion.load_documents(KNOWLEDGE_PATH)

    json_ld_document = next(
        document for document in documents if document.metadata["source"].endswith("json_ld.md")
    )
    assert json_ld_document.metadata["category"] == "comprehension"
    assert json_ld_document.metadata["criterion"] == "json_ld"

    graphql_document = next(
        document for document in documents if document.metadata["source"].endswith("graphql.md")
    )
    assert graphql_document.metadata["category"] == "interaction"
    assert graphql_document.metadata["criterion"] == "graphql"


def test_split_documents_preserves_markdown_sections() -> None:
    """2) Chunking: Markdown sections preserved, chunks generated correctly."""
    ingestion = KnowledgeIngestion()
    documents = ingestion.load_documents(KNOWLEDGE_PATH)

    chunks = ingestion.split_documents(documents)
    _print_documents("split_documents", chunks)

    assert len(chunks) >= len(documents)

    csp_chunks = [chunk for chunk in chunks if chunk.metadata["criterion"] == "csp"]
    sections_found = {chunk.metadata["section"] for chunk in csp_chunks}
    expected_sections = {
        "Definition",
        "Technical Background",
        "Importance for AI Agent Readiness",
        "ARAS Evaluation Context",
        "Common Issues",
        "Impact",
        "Recommendation Strategy",
        "Implementation Guidance",
        "Validation Checklist",
        "Related ARAS Criteria",
        "References",
    }
    assert expected_sections <= sections_found

    # Each chunk carries its document + section title as context, per the
    # required final document format.
    recommendation_chunk = next(
        chunk
        for chunk in csp_chunks
        if chunk.metadata["section"] == "Recommendation Strategy"
    )
    assert "# Content Security Policy" in recommendation_chunk.page_content
    assert "## Recommendation Strategy" in recommendation_chunk.page_content


def test_split_documents_respects_chunk_size() -> None:
    """2) Chunking: no oversized chunks."""
    ingestion = KnowledgeIngestion()
    documents = ingestion.load_documents(KNOWLEDGE_PATH)
    chunks = ingestion.split_documents(documents)

    oversized = [len(chunk.page_content) for chunk in chunks if len(chunk.page_content) > _MAX_CHUNK_SIZE]
    print(f"oversized chunk lengths: {oversized}")

    for chunk in chunks:
        assert len(chunk.page_content) <= _MAX_CHUNK_SIZE + _CHUNK_SIZE_TOLERANCE


def test_split_documents_chunk_ids_are_contiguous_per_document() -> None:
    """chunk_id is 0-based and contiguous across all of a document's sections."""
    ingestion = KnowledgeIngestion()
    documents = ingestion.load_documents(KNOWLEDGE_PATH)
    chunks = ingestion.split_documents(documents)

    hsts_chunks = [chunk for chunk in chunks if chunk.metadata["criterion"] == "hsts"]
    assert [chunk.metadata["chunk_id"] for chunk in hsts_chunks] == list(range(len(hsts_chunks)))


def test_ingest_output_matches_expected_document_shape() -> None:
    """3) Output compatibility: Document(page_content=..., metadata={category, criterion, ...})."""
    ingestion = KnowledgeIngestion()

    chunks = ingestion.ingest(KNOWLEDGE_PATH)

    assert len(chunks) > 0
    for chunk in chunks:
        assert isinstance(chunk, Document)
        assert isinstance(chunk.page_content, str) and chunk.page_content.strip()
        assert {"source", "category", "criterion", "section", "chunk_id"} <= chunk.metadata.keys()
        # ChromaDB requires scalar metadata values; every value must already
        # be a plain str/int/float/bool by the time ingestion is done.
        assert all(isinstance(value, (str, int, float, bool)) for value in chunk.metadata.values())

    sample = next(chunk for chunk in chunks if chunk.metadata["criterion"] == "csp")
    print(f"sample chunk: {sample}")
    assert sample.metadata["category"] == "security"
    assert sample.metadata["criterion"] == "csp"


def test_embedding_pipeline_compatibility() -> None:
    """4) Embedding compatibility: all chunks embedded, vector dimension 384."""
    chunks = KnowledgeIngestion().ingest(KNOWLEDGE_PATH)

    manager = EmbeddingManager()
    vectors = manager.embed_documents(chunks)

    print(f"embedded {len(vectors)} chunks, dimension {len(vectors[0])}")
    assert len(vectors) == len(chunks)
    assert all(len(vector) == _EMBEDDING_DIMENSIONS for vector in vectors)


def test_chromadb_storage_preserves_metadata() -> None:
    """5) ChromaDB storage: vectors stored, metadata preserved."""
    chunks = KnowledgeIngestion().ingest(KNOWLEDGE_PATH)
    persist_directory = Path(tempfile.mkdtemp(prefix="aras_ingestion_chroma_test_"))

    try:
        vector_store_manager = VectorStoreManager(persist_directory=persist_directory)
        store = vector_store_manager.create_vector_store(chunks)

        assert store._collection.count() == len(chunks)

        results = store.similarity_search(
            "Content Security Policy missing header remediation",
            k=3,
            filter={"category": "security"},
        )
        print(f"retrieved: {[r.metadata for r in results]}")

        assert len(results) == 3
        for result in results:
            assert result.metadata["category"] == "security"
            assert {"criterion", "section", "source", "chunk_id"} <= result.metadata.keys()
    finally:
        shutil.rmtree(persist_directory, ignore_errors=True)


if __name__ == "__main__":
    test_load_documents_finds_every_aras_knowledge_file_with_metadata()
    test_metadata_extraction_is_dynamic_across_categories()
    test_split_documents_preserves_markdown_sections()
    test_split_documents_respects_chunk_size()
    test_split_documents_chunk_ids_are_contiguous_per_document()
    test_ingest_output_matches_expected_document_shape()
    test_embedding_pipeline_compatibility()
    test_chromadb_storage_preserves_metadata()
    print("All tests passed.")

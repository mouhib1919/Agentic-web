"""Document ingestion pipeline for the ARAS Recommendation Agent's RAG stack.

This module is the first stage of the Retrieval-Augmented Generation
pipeline: it loads the Markdown knowledge base created for each ARAS
dimension (Discoverability, Comprehension, Interaction, Security),
converts each file into a LangChain `Document`, attaches metadata
derived from the file's location, and splits long documents into
retrieval-sized chunks.

This module MUST NOT:
    - create embeddings
    - use ChromaDB or any other vector store
    - call any LLM
    - perform retrieval
    - generate recommendations

Those responsibilities belong to later RAG components (embeddings,
vector storage, retriever, generation) built on top of this ingestion
layer's output.
"""

from __future__ import annotations

from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

_MARKDOWN_GLOB = "**/*.md"
_CHUNK_SIZE = 1500
_CHUNK_OVERLAP = 200


class KnowledgeIngestion:
    """Loads and prepares the ARAS knowledge base for embedding.

    This class holds no embedding, vector-storage, retrieval, or
    generation logic. It is a pure transformation step: Markdown files
    on disk in -> chunked, metadata-rich `Document` objects out, ready
    for a later embedding stage to consume.
    """

    def __init__(
        self,
        chunk_size: int = _CHUNK_SIZE,
        chunk_overlap: int = _CHUNK_OVERLAP,
    ) -> None:
        """Initialize the ingestion pipeline.

        Args:
            chunk_size: Maximum character length of each chunk
                produced by `split_documents`.
            chunk_overlap: Number of overlapping characters retained
                between consecutive chunks of the same document, to
                avoid losing context at chunk boundaries.
        """
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    def ingest(self, knowledge_path: str) -> list[Document]:
        """Run the full ingestion pipeline: load, then split.

        Args:
            knowledge_path: Path to the root of the knowledge base
                (e.g. `recommendation/knowledge`), containing one
                subdirectory per ARAS dimension.

        Returns:
            Every knowledge document, split into retrieval-sized
            chunks with metadata preserved, ready for embedding.
        """
        documents = self.load_documents(knowledge_path)
        return self.split_documents(documents)

    # ------------------------------------------------------------------
    # 1. Loading
    # ------------------------------------------------------------------

    def load_documents(self, knowledge_path: str) -> list[Document]:
        """Recursively load every Markdown file under `knowledge_path`.

        Args:
            knowledge_path: Path to the root of the knowledge base.

        Returns:
            One `Document` per Markdown file found, with `page_content`
            set to the file's full text and `metadata` populated from
            its location (see `_extract_metadata`). Files are returned
            in sorted path order for deterministic output.
        """
        knowledge_root = Path(knowledge_path)
        file_paths = sorted(knowledge_root.glob(_MARKDOWN_GLOB))

        documents: list[Document] = []
        for file_path in file_paths:
            content = file_path.read_text(encoding="utf-8")
            metadata = self._extract_metadata(file_path, knowledge_root)
            documents.append(Document(page_content=content, metadata=metadata))

        return documents

    @staticmethod
    def _extract_metadata(file_path: Path, knowledge_root: Path) -> dict[str, str]:
        """Derive category/topic/source metadata from a knowledge file's path.

        The category is the file's immediate parent directory name
        relative to `knowledge_root` (e.g. `security`, `comprehension`)
        and is never hardcoded — it is read directly from the
        directory structure, so adding a new dimension folder requires
        no code change here. The topic is the filename without its
        extension.

        Args:
            file_path: Absolute or relative path to a single `.md` file.
            knowledge_root: Path to the root of the knowledge base that
                `file_path` was discovered under.

        Returns:
            A dict with `category`, `topic`, and `source` keys, e.g.
            `{"category": "security", "topic": "csp",
            "source": "knowledge/security/csp.md"}`.
        """
        relative_to_root = file_path.relative_to(knowledge_root)
        category = relative_to_root.parts[0]
        topic = file_path.stem
        source = (knowledge_root.name / relative_to_root).as_posix()

        return {"category": category, "topic": topic, "source": source}

    # ------------------------------------------------------------------
    # 2. Splitting
    # ------------------------------------------------------------------

    def split_documents(self, documents: list[Document]) -> list[Document]:
        """Split documents into retrieval-sized chunks, preserving metadata.

        Uses `RecursiveCharacterTextSplitter`, which splits on a
        hierarchy of separators (paragraphs, then lines, then words)
        so chunk boundaries fall on natural text breaks rather than
        mid-sentence, preserving semantic coherence. A document shorter
        than `chunk_size` yields a single chunk rather than being
        split unnecessarily.

        Args:
            documents: The documents to split, as produced by
                `load_documents`.

        Returns:
            One or more chunks per input document. Each chunk carries
            every metadata key from its source document plus a
            `chunk_id` index (0-based) identifying its position within
            that document.
        """
        chunked_documents: list[Document] = []
        for document in documents:
            chunk_texts = self._splitter.split_text(document.page_content)
            for chunk_index, chunk_text in enumerate(chunk_texts):
                chunk_metadata = {**document.metadata, "chunk_id": chunk_index}
                chunked_documents.append(
                    Document(page_content=chunk_text, metadata=chunk_metadata)
                )

        return chunked_documents

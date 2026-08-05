"""Document ingestion pipeline for the ARAS Recommendation Agent's RAG stack.

This module is the first stage of the Retrieval-Augmented Generation
pipeline: it loads the ARAS knowledge base (`knowledge/aras_knowledge/`,
one Markdown file per criterion, one subdirectory per ARAS dimension),
extracts each file's YAML frontmatter metadata, splits it in two stages
(Markdown-structure-aware, then character-based) to preserve section
context, and returns enriched, metadata-rich LangChain `Document`
chunks ready for embedding.

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

import re
from pathlib import Path
from typing import Any, Optional

import yaml
from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

_MARKDOWN_GLOB = "**/*.md"
_CHUNK_SIZE = 1500
_CHUNK_OVERLAP = 200

# Stage 1 splits on Markdown headers so each resulting piece stays
# aligned with the document's own section structure (e.g. the ARAS
# document template's "## Recommendation Strategy" section) rather
# than being cut at an arbitrary character offset.
_MARKDOWN_HEADERS_TO_SPLIT_ON: list[tuple[str, str]] = [
    ("#", "document_title"),
    ("##", "section"),
]

_FRONTMATTER_PATTERN = re.compile(r"\A---\s*\n(.*?\n)---\s*\n?", re.DOTALL)
_H1_PATTERN = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)


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
                produced by the stage-2 splitter in `split_documents`.
            chunk_overlap: Number of overlapping characters retained
                between consecutive stage-2 chunks of the same
                section, to avoid losing context at chunk boundaries.
        """
        self._markdown_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=_MARKDOWN_HEADERS_TO_SPLIT_ON,
            strip_headers=True,
        )
        self._character_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    def ingest(self, knowledge_path: str) -> list[Document]:
        """Run the full ingestion pipeline: load, then split.

        Args:
            knowledge_path: Path to the root of the knowledge base
                (e.g. `knowledge/aras_knowledge`), containing one
                subdirectory per ARAS dimension.

        Returns:
            Every knowledge document, split into retrieval-sized
            chunks with metadata preserved, ready for embedding.
        """
        documents = self.load_documents(knowledge_path)
        return self.split_documents(documents)

    # ------------------------------------------------------------------
    # 1. Loading + metadata extraction
    # ------------------------------------------------------------------

    def load_documents(self, knowledge_path: str) -> list[Document]:
        """Recursively load every Markdown file under `knowledge_path`.

        Each file's YAML frontmatter (if present) is parsed and
        attached as metadata, and stripped from the returned
        `page_content` so it never leaks into embedded text or
        Markdown-header splitting downstream.

        Args:
            knowledge_path: Path to the root of the knowledge base.

        Returns:
            One `Document` per Markdown file found, with `page_content`
            set to the file's body (frontmatter stripped) and
            `metadata` populated from the frontmatter, falling back to
            path-derived values for any field the frontmatter omits.
            Files are returned in sorted path order for deterministic
            output.
        """
        knowledge_root = Path(knowledge_path)
        file_paths = sorted(knowledge_root.glob(_MARKDOWN_GLOB))

        documents: list[Document] = []
        for file_path in file_paths:
            raw_content = file_path.read_text(encoding="utf-8")
            frontmatter, body = self._split_frontmatter(raw_content)
            metadata = self._extract_metadata(file_path, knowledge_root, frontmatter)
            documents.append(Document(page_content=body, metadata=metadata))

        return documents

    @staticmethod
    def _split_frontmatter(raw_content: str) -> tuple[dict[str, Any], str]:
        """Split a Markdown file's leading YAML frontmatter from its body.

        Args:
            raw_content: The full, unmodified text of a Markdown file.

        Returns:
            A tuple of `(frontmatter, body)`. `frontmatter` is the
            parsed YAML block as a dict (empty if the file has no
            frontmatter or it fails to parse as a mapping). `body` is
            `raw_content` with the frontmatter block removed.
        """
        match = _FRONTMATTER_PATTERN.match(raw_content)
        if not match:
            return {}, raw_content

        body = raw_content[match.end() :]
        try:
            parsed = yaml.safe_load(match.group(1))
        except yaml.YAMLError:
            return {}, body

        return (parsed if isinstance(parsed, dict) else {}), body

    @classmethod
    def _extract_metadata(
        cls, file_path: Path, knowledge_root: Path, frontmatter: dict[str, Any]
    ) -> dict[str, Any]:
        """Build a document's base metadata from its frontmatter and file path.

        Every frontmatter field is preserved as metadata (list values,
        e.g. `related:`, are joined into a comma-separated string,
        since ChromaDB metadata values must be scalar). `category` and
        `criterion` fall back to path-derived values — the immediate
        parent directory name and the filename stem, respectively — so
        a file with no frontmatter (or a missing individual field)
        still receives usable metadata rather than failing ingestion.

        Args:
            file_path: Absolute or relative path to a single `.md` file.
            knowledge_root: Path to the root of the knowledge base that
                `file_path` was discovered under.
            frontmatter: The file's parsed YAML frontmatter, possibly empty.

        Returns:
            A dict of scalar metadata values, always including
            `source`, `category`, and `criterion`.
        """
        relative_to_root = file_path.relative_to(knowledge_root)
        source = (knowledge_root.name / relative_to_root).as_posix()

        metadata: dict[str, Any] = {"source": source}
        for key, value in frontmatter.items():
            metadata[key] = ", ".join(str(item) for item in value) if isinstance(value, list) else value

        metadata.setdefault("category", relative_to_root.parts[0])
        metadata.setdefault("criterion", file_path.stem)

        return metadata

    # ------------------------------------------------------------------
    # 2. Splitting (Markdown-structure-aware, then character-based)
    # ------------------------------------------------------------------

    def split_documents(self, documents: list[Document]) -> list[Document]:
        """Split documents into retrieval-sized chunks, preserving metadata.

        Applies a two-stage strategy per document:

        Stage 1 — `MarkdownHeaderTextSplitter` splits each document
        along its own `#`/`##` structure, so a chunk never straddles
        two unrelated sections (e.g. mixing "Common Issues" with
        "Recommendation Strategy"). The document title (`#`) and
        section title (`##`) are captured for every resulting piece.

        Stage 2 — `RecursiveCharacterTextSplitter` further splits any
        section still longer than `chunk_size`, on a hierarchy of
        separators (paragraphs, then lines, then sentences) so
        sub-chunk boundaries fall on natural text breaks. A section
        shorter than `chunk_size` is not split further.

        Each final chunk's `page_content` is prefixed with its
        document and section titles, so the embedded text carries its
        own context even in isolation from the rest of the document.

        Args:
            documents: The documents to split, as produced by
                `load_documents`.

        Returns:
            One or more chunks per input document. Each chunk carries
            every metadata key from its source document, plus
            `section` (the enclosing `##` heading) and a `chunk_id`
            index (0-based, contiguous across all of that document's
            sections).
        """
        chunked_documents: list[Document] = []
        for document in documents:
            chunked_documents.extend(self._split_single_document(document))
        return chunked_documents

    def _split_single_document(self, document: Document) -> list[Document]:
        """Apply the two-stage split to a single document.

        Args:
            document: One document, as produced by `load_documents`.

        Returns:
            The ordered list of chunks derived from this document.
        """
        document_title = self._extract_document_title(document.page_content)
        header_sections = self._markdown_splitter.split_text(document.page_content)

        chunks: list[Document] = []
        chunk_id = 0
        for section in header_sections:
            section_title = section.metadata.get("section", "")
            for chunk_text in self._character_splitter.split_text(section.page_content):
                chunks.append(
                    Document(
                        page_content=self._compose_chunk_content(
                            document_title, section_title, chunk_text
                        ),
                        metadata={
                            **document.metadata,
                            "section": section_title,
                            "chunk_id": chunk_id,
                        },
                    )
                )
                chunk_id += 1

        return chunks

    @staticmethod
    def _extract_document_title(body: str) -> str:
        """Extract a document's top-level (`#`) title from its body text.

        Args:
            body: The document's Markdown content (frontmatter already
                stripped).

        Returns:
            The title text following the first `# ` heading, or an
            empty string if the document has no top-level heading.
        """
        match = _H1_PATTERN.search(body)
        return match.group(1) if match else ""

    @staticmethod
    def _compose_chunk_content(document_title: str, section_title: str, chunk_text: str) -> str:
        """Prefix a chunk's text with its document and section titles.

        Keeps each chunk self-describing (which document, which
        section) even when retrieved in isolation, without requiring a
        consumer to cross-reference metadata to know what it is reading.

        Args:
            document_title: The source document's `#` title.
            section_title: The enclosing `##` section title.
            chunk_text: The chunk's own text content.

        Returns:
            The composed chunk content.
        """
        heading_lines = [line for line in (f"# {document_title}" if document_title else "", f"## {section_title}" if section_title else "") if line]
        return "\n\n".join([*heading_lines, chunk_text]) if heading_lines else chunk_text

"""Semantic retrieval for the ARAS Recommendation Agent's RAG stack.

This module is the fourth stage of the Retrieval-Augmented Generation
pipeline: given a natural-language query describing a detected
readiness gap (e.g. "Missing Content Security Policy header"), it
searches the already-persisted ChromaDB vector store and returns the
most semantically relevant knowledge chunks.

This module MUST NOT:
    - generate recommendations
    - call any LLM
    - modify documents
    - create embeddings manually (embedding is delegated to
      `EmbeddingManager` via `VectorStoreManager`)
    - perform document ingestion

Those responsibilities belong to other RAG components (ingestion,
embeddings, vector storage, generation) built around this one.

This module defines two retrievers:

    - `KnowledgeRetriever`: a thin wrapper around the persisted Chroma
      collection, offering plain similarity search. Used as-is by
      `RecommendationAgent` today.
    - `ARASRetriever`: an ARAS-specific intelligent retriever built on
      top of `KnowledgeRetriever`, adding metadata-filtered bi-encoder
      retrieval followed by cross-encoder re-ranking. It does not
      replace `KnowledgeRetriever` — it composes it.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Optional

from langchain_chroma import Chroma
from langchain_core.documents import Document
from sentence_transformers import CrossEncoder

from recommendation.rag.vector_store import VectorStoreManager

_DEFAULT_K = 5


class KnowledgeRetriever:
    """Retrieves the most relevant ARAS knowledge chunks for a query.

    This class holds no ingestion, embedding, or vector-storage
    creation logic of its own — it delegates to `VectorStoreManager`
    to load the already-persisted ChromaDB collection (built earlier
    in the pipeline), and only adds the query-time similarity search
    behavior on top of it.
    """

    def __init__(self) -> None:
        """Construct an uninitialized retriever.

        `initialize()` must be called before `retrieve()` can be used;
        this keeps constructing an instance cheap (no disk or model
        loading) and makes the loading step explicit and testable.
        """
        self._vector_store: Optional[Chroma] = None

    def initialize(self, vector_store_path: str) -> None:
        """Load the existing ChromaDB collection and its embedding model.

        Args:
            vector_store_path: Filesystem directory a `VectorStoreManager`
                has already persisted a Chroma collection to (e.g. via
                `VectorStoreManager.create_vector_store`).

        Raises:
            FileNotFoundError: If no persisted vector store exists yet
                at `vector_store_path`. The retriever only loads an
                existing collection; it does not embed or ingest
                documents itself.
        """
        vector_store_manager = VectorStoreManager(persist_directory=Path(vector_store_path))
        vector_store = vector_store_manager.load_vector_store()

        if vector_store is None:
            raise FileNotFoundError(
                f"No vector store found at '{vector_store_path}'. "
                "Run the ingestion and vector store creation steps first."
            )

        self._vector_store = vector_store

    @property
    def is_initialized(self) -> bool:
        """Whether `initialize()` has successfully loaded a vector store."""
        return self._vector_store is not None

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def retrieve(
        self,
        query: str,
        k: int = _DEFAULT_K,
        filter: Optional[dict[str, Any]] = None,
    ) -> list[Document]:
        """Retrieve the top-k most semantically relevant knowledge chunks.

        Embeds `query` with the same embedding model used to build the
        vector store, then performs a similarity search against
        ChromaDB. Every returned `Document` preserves its original
        `page_content` and `metadata` (`category`, `topic`, `source`,
        `chunk_id`) unchanged.

        Args:
            query: A natural-language description of the readiness gap
                or topic to find documentation for (e.g. "Missing
                Content Security Policy header").
            k: Maximum number of chunks to return.
            filter: Optional ChromaDB metadata filter (e.g.
                `{"category": "security"}`) restricting the search to
                chunks matching the given metadata. When omitted, the
                search runs over the entire knowledge base.

        Returns:
            The top-k most relevant `Document` chunks, ranked by
            similarity to `query`, most relevant first.
        """
        vector_store = self._require_vector_store()
        return vector_store.similarity_search(query, k=k, filter=filter)

    def retrieve_with_scores(
        self,
        query: str,
        k: int = _DEFAULT_K,
        filter: Optional[dict[str, Any]] = None,
    ) -> list[tuple[Document, float]]:
        """Retrieve the top-k most relevant chunks alongside their distance score.

        Identical to `retrieve`, but also returns each chunk's
        similarity distance so callers (e.g. debugging or reporting
        tools) can inspect how confidently a chunk matched the query.
        Lower scores indicate a closer semantic match, since ChromaDB
        reports distance rather than a normalized similarity.

        Args:
            query: The natural-language query to search for.
            k: Maximum number of chunks to return.
            filter: Optional ChromaDB metadata filter, as in `retrieve`.

        Returns:
            The top-k `(Document, distance_score)` pairs, most relevant
            (lowest distance) first.
        """
        vector_store = self._require_vector_store()
        return vector_store.similarity_search_with_score(query, k=k, filter=filter)

    def _require_vector_store(self) -> Chroma:
        """Return the loaded vector store, or raise if not yet initialized.

        Returns:
            The `Chroma` vector store loaded by `initialize`.

        Raises:
            RuntimeError: If `initialize()` has not been called yet.
        """
        if self._vector_store is None:
            raise RuntimeError(
                "KnowledgeRetriever is not initialized. Call initialize() first."
            )
        return self._vector_store


# A small, free, locally-run cross-encoder used only to re-rank the
# bi-encoder's already-narrowed candidate set. Re-ranking the full
# knowledge base with a cross-encoder would be too slow to be useful;
# scoring ~10 candidates per issue is not.
_DEFAULT_CROSS_ENCODER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
_DEFAULT_CANDIDATE_K = 10
_DEFAULT_TOP_N = 3
_DEFAULT_SCORE_THRESHOLD = 0.70
_RECOMMENDATION_OBJECTIVE = "Generate remediation steps to improve AI agent readiness."

# Per-criterion overrides for how many bi-encoder candidates to pull
# before re-ranking. A criterion with few, narrowly-scoped chunks (e.g.
# a single-topic security header) needs fewer candidates than one whose
# knowledge document covers a broader surface (e.g. API documentation).
_TOP_K_OVERRIDES: dict[tuple[str, str], int] = {
    ("security", "csp"): 5,
    ("interaction", "api_documentation"): 10,
}


class ARASRetriever:
    """ARAS-specific intelligent retriever: metadata filter + bi-encoder + re-ranker.

    This class holds no ingestion, embedding, or vector-storage
    creation logic of its own — it composes a `KnowledgeRetriever` for
    the metadata-filtered bi-encoder search stage, and adds a
    cross-encoder re-ranking stage on top of it. It never calls an LLM
    and never generates recommendation text; its only output is a
    ranked list of `Document` chunks for `RecommendationAgent` to
    consume.

    Pipeline: recommendation context -> query builder -> metadata
    filtering -> bi-encoder semantic retrieval (top-k candidates) ->
    cross-encoder re-ranking -> relevance threshold -> top-n documents.
    """

    def __init__(
        self,
        knowledge_retriever: Optional[KnowledgeRetriever] = None,
        cross_encoder_model: str = _DEFAULT_CROSS_ENCODER_MODEL,
        candidate_k: int = _DEFAULT_CANDIDATE_K,
        top_n: int = _DEFAULT_TOP_N,
        score_threshold: float = _DEFAULT_SCORE_THRESHOLD,
        top_k_overrides: Optional[dict[tuple[str, str], int]] = None,
    ) -> None:
        """Configure the ARAS retriever's collaborators and tuning parameters.

        Args:
            knowledge_retriever: The bi-encoder retriever to use for
                the metadata-filtered semantic search stage. A new,
                uninitialized `KnowledgeRetriever` is created if
                omitted; `initialize()` must still be called before use.
            cross_encoder_model: HuggingFace Hub identifier of the
                cross-encoder re-ranking model. Not loaded until first
                needed, mirroring `EmbeddingManager`'s lazy-loading.
            candidate_k: Default number of bi-encoder candidates to
                retrieve before re-ranking, for criteria with no entry
                in `top_k_overrides`.
            top_n: Maximum number of re-ranked documents to return.
            score_threshold: Minimum normalized (sigmoid) cross-encoder
                relevance score a document must reach to be returned.
                Documents scoring below this are dropped rather than
                passed on as weak/irrelevant context.
            top_k_overrides: Per-`(category, criterion)` candidate_k
                overrides. Defaults to `_TOP_K_OVERRIDES`; pass a
                custom mapping to reconfigure without editing this module.
        """
        self._retriever = knowledge_retriever or KnowledgeRetriever()
        self._cross_encoder_model_name = cross_encoder_model
        self._cross_encoder: Optional[CrossEncoder] = None
        self._candidate_k = candidate_k
        self._top_n = top_n
        self._score_threshold = score_threshold
        self._top_k_overrides = dict(top_k_overrides) if top_k_overrides else dict(_TOP_K_OVERRIDES)

    def initialize(self, vector_store_path: str) -> None:
        """Load the underlying `KnowledgeRetriever`'s persisted ChromaDB collection.

        Args:
            vector_store_path: Filesystem directory a `VectorStoreManager`
                has already persisted a Chroma collection to.

        Raises:
            FileNotFoundError: If no persisted vector store exists yet
                at `vector_store_path`.
        """
        self._retriever.initialize(vector_store_path)

    @property
    def is_initialized(self) -> bool:
        """Whether `initialize()` has successfully loaded a vector store."""
        return self._retriever.is_initialized

    @property
    def cross_encoder(self) -> CrossEncoder:
        """The underlying cross-encoder re-ranking model, loaded lazily.

        Returns:
            A `CrossEncoder` instance backed by `cross_encoder_model`.

        Raises:
            RuntimeError: If the model fails to load (e.g. an invalid
                model name, or weights cannot be downloaded/read from
                the local cache).
        """
        if self._cross_encoder is None:
            try:
                self._cross_encoder = CrossEncoder(self._cross_encoder_model_name)
            except Exception as exc:  # noqa: BLE001 - normalize into one clear, catchable error
                raise RuntimeError(
                    f"Failed to load cross-encoder model '{self._cross_encoder_model_name}': {exc}"
                ) from exc
        return self._cross_encoder

    # ------------------------------------------------------------------
    # Query builder
    # ------------------------------------------------------------------

    @staticmethod
    def build_query(context: dict[str, Any]) -> str:
        """Build a structured natural-language query from an ARAS recommendation context.

        Args:
            context: The Rule Engine's recommendation context, e.g.
                `{"category": "security", "criterion": "csp", "issue":
                "Missing CSP header", "priority": "HIGH"}`. Only
                `category`, `criterion`, and `issue` are read here;
                `priority` (and any other field) is not part of the
                query text, since it does not affect which knowledge is
                relevant.

        Returns:
            A structured natural-language query combining the
            dimension, criterion, detected issue, and the fixed
            recommendation objective.
        """
        category = context.get("category", "")
        criterion = context.get("criterion", "")
        issue = context.get("issue", "")

        return (
            f"ARAS Dimension: {category}\n\n"
            f"Criterion: {criterion}\n\n"
            f"Detected Issue:\n{issue}\n\n"
            f"Objective:\n{_RECOMMENDATION_OBJECTIVE}"
        )

    @staticmethod
    def _build_rerank_query(context: dict[str, Any]) -> str:
        """Build the short query used for cross-encoder re-ranking.

        `cross-encoder/ms-marco-MiniLM-L-6-v2` is trained on short,
        MS MARCO-style queries paired with a single passage; feeding it
        the full structured `build_query` output (four labeled
        sections, mostly boilerplate) dilutes the query-passage
        relevance signal and suppresses every candidate's score. The
        bi-encoder benefits from that fuller structured context, but
        the cross-encoder does not — so re-ranking uses a concise
        "detected issue + criterion" query instead.

        Args:
            context: The recommendation context passed to `retrieve`.

        Returns:
            A short natural-language query combining the criterion and
            detected issue.
        """
        criterion = context.get("criterion", "")
        issue = context.get("issue", "")
        return f"{issue} {criterion}".strip()

    # ------------------------------------------------------------------
    # Metadata filtering + dynamic top-k
    # ------------------------------------------------------------------

    def _resolve_candidate_k(self, category: str, criterion: str) -> int:
        """Resolve how many bi-encoder candidates to retrieve for a given criterion.

        Args:
            category: The ARAS dimension of the issue being retrieved for.
            criterion: The specific criterion of the issue.

        Returns:
            The configured override for `(category, criterion)`, or
            `candidate_k` if none is configured.
        """
        return self._top_k_overrides.get((category, criterion), self._candidate_k)

    @staticmethod
    def _build_metadata_filter(context: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Build a ChromaDB metadata filter from `category`/`criterion`.

        Filtering by metadata before semantic search narrows the
        search space to only the knowledge chunks that could possibly
        be relevant (e.g. `criterion=csp` never matches a
        `criterion=graphql` chunk), regardless of how semantically
        similar their text might otherwise appear to the query.

        Args:
            context: The recommendation context passed to `retrieve`.

        Returns:
            `None` if neither `category` nor `criterion` is present;
            a single-field filter if only one is present; otherwise a
            `$and` filter combining both fields (Chroma's required
            syntax for multi-field filters).
        """
        clauses = [
            {field: context[field]}
            for field in ("category", "criterion")
            if context.get(field)
        ]
        if not clauses:
            return None
        if len(clauses) == 1:
            return clauses[0]
        return {"$and": clauses}

    # ------------------------------------------------------------------
    # Full pipeline
    # ------------------------------------------------------------------

    def retrieve(self, context: dict[str, Any]) -> list[Document]:
        """Retrieve the most relevant knowledge chunks for an ARAS recommendation context.

        Runs the full pipeline: build a structured query, filter by
        metadata, retrieve bi-encoder candidates, re-rank them with the
        cross-encoder, and drop anything below `score_threshold`.

        Args:
            context: The Rule Engine's recommendation context, e.g.
                `{"category": "security", "criterion": "csp", "issue":
                "Missing CSP header", "priority": "HIGH"}`.

        Returns:
            Up to `top_n` `Document` chunks, most relevant first, with
            their original `page_content` and metadata unchanged.
            Returns `[]` (never raises) if the retriever is not
            initialized, no candidates match the metadata filter, or
            every candidate scores below `score_threshold`.
        """
        if not self.is_initialized:
            return []

        category = context.get("category", "")
        criterion = context.get("criterion", "")
        query = self.build_query(context)
        candidate_k = self._resolve_candidate_k(category, criterion)
        metadata_filter = self._build_metadata_filter(context)

        try:
            candidates = self._retriever.retrieve(query, k=candidate_k, filter=metadata_filter)
        except Exception:  # noqa: BLE001 - unknown criterion / empty knowledge -> no results
            return []

        if not candidates:
            return []

        return self._rerank(self._build_rerank_query(context), candidates)

    def _rerank(self, rerank_query: str, candidates: list[Document]) -> list[Document]:
        """Re-rank bi-encoder candidates with the cross-encoder and apply the threshold.

        Args:
            rerank_query: The short query built by `_build_rerank_query`
                — deliberately more concise than the bi-encoder's
                structured `build_query` output (see its docstring).
            candidates: The bi-encoder's candidate chunks, already
                metadata-filtered.

        Returns:
            Up to `top_n` candidates whose normalized relevance score
            is at least `score_threshold`, most relevant first.
        """
        pairs = [(rerank_query, candidate.page_content) for candidate in candidates]
        try:
            raw_scores = self.cross_encoder.predict(pairs)
        except Exception as exc:  # noqa: BLE001 - normalize into one clear, catchable error
            raise RuntimeError(f"Cross-encoder re-ranking failed: {exc}") from exc

        ranked = sorted(
            zip(candidates, self._normalize_scores(raw_scores)),
            key=lambda pair: pair[1],
            reverse=True,
        )
        relevant = [document for document, score in ranked if score >= self._score_threshold]
        return relevant[: self._top_n]

    @staticmethod
    def _normalize_scores(raw_scores: Any) -> list[float]:
        """Normalize raw cross-encoder logits into a [0, 1] relevance score via sigmoid.

        The `cross-encoder/ms-marco-MiniLM-L-6-v2` model outputs
        unbounded relevance logits, not a probability — `score_threshold`
        is only meaningful once scores are mapped onto a comparable
        [0, 1] scale.

        Args:
            raw_scores: The cross-encoder's raw `predict()` output,
                one score per (query, candidate) pair.

        Returns:
            One sigmoid-normalized score per input score, in [0, 1].
        """
        return [1.0 / (1.0 + math.exp(-float(score))) for score in raw_scores]

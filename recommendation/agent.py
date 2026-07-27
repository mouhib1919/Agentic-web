"""Recommendation Agent.

This module is the final analysis layer of ARAS. It turns each
`ClassifiedIssue` produced by the Rule Engine into a professional,
actionable `Recommendation`, by retrieving grounding documentation
from the RAG knowledge base and asking an `LLMClient` to expand it
into an explanation, a recommendation, and concrete implementation
steps.

This agent MUST NOT:
    - collect website evidence
    - analyze websites
    - calculate scores
    - classify priorities (it only carries over what the Rule Engine
      already decided)
    - modify Rule Engine decisions
    - directly access raw HTML
    - duplicate retriever, embedding, vector-store, or rule-engine logic

Those responsibilities belong to earlier ARAS layers. This agent only
orchestrates already-built components: `KnowledgeRetriever`,
`PromptBuilder`, and `LLMClient`.
"""

from __future__ import annotations

import re
from typing import Optional

from langchain_core.documents import Document

from models.recommendation import Recommendation, RecommendationResult
from models.rule_engine import ClassifiedIssue
from recommendation.llm_client import GroqLLMClient, LLMClient
from recommendation.prompt_builder import (
    EXPLANATION_HEADER,
    IMPLEMENTATION_STEPS_HEADER,
    RECOMMENDATION_HEADER,
    PromptBuilder,
)
from recommendation.rag.retriever import KnowledgeRetriever

_DEFAULT_RETRIEVAL_K = 3
_PRIORITY_LEVELS = ("HIGH", "MEDIUM", "LOW")


class RecommendationAgent:
    """Generates a professional recommendation for every classified issue.

    This class holds no retrieval, embedding, vector-storage, or
    priority-classification logic of its own — it delegates entirely
    to an already-built `KnowledgeRetriever`, `PromptBuilder`, and
    `LLMClient`, and only orchestrates the flow between them.
    """

    def __init__(
        self,
        retriever: Optional[KnowledgeRetriever] = None,
        prompt_builder: Optional[PromptBuilder] = None,
        llm_client: Optional[LLMClient] = None,
        retrieval_k: int = _DEFAULT_RETRIEVAL_K,
    ) -> None:
        """Configure the Recommendation Agent's collaborators.

        Args:
            retriever: A `KnowledgeRetriever`, ideally already
                initialized via `retriever.initialize(vector_store_path)`.
                If omitted, an uninitialized `KnowledgeRetriever` is
                used, which causes every issue to fall back to
                generation without retrieved documentation (see
                `_retrieve_documents`) — retrieval failure is handled
                gracefully, not treated as fatal.
            prompt_builder: The prompt builder to use. A default
                `PromptBuilder` is created if omitted.
            llm_client: The LLM backend to use. Defaults to
                `GroqLLMClient` (LangChain + Groq, requires
                `GROQ_API_KEY`), and can be swapped for any other
                `LLMClient` implementation — e.g. `TemplateLLMClient`
                for offline tests — without changing this class.
            retrieval_k: Number of documents to retrieve per issue.
        """
        self._retriever = retriever or KnowledgeRetriever()
        self._prompt_builder = prompt_builder or PromptBuilder()
        self._llm_client = llm_client or GroqLLMClient()
        self._retrieval_k = retrieval_k

    def generate(self, classified_issues: list[ClassifiedIssue]) -> RecommendationResult:
        """Generate a recommendation for every classified issue.

        Args:
            classified_issues: The Rule Engine's output — one
                `ClassifiedIssue` per detected readiness gap.

        Returns:
            A `RecommendationResult` with one `Recommendation` per
            input issue and a priority-level summary count.
        """
        recommendations = [
            self._generate_one(classified_issue) for classified_issue in classified_issues
        ]
        return RecommendationResult(
            recommendations=recommendations,
            summary=self._summarize(recommendations),
        )

    # ------------------------------------------------------------------
    # Per-issue generation
    # ------------------------------------------------------------------

    def _generate_one(self, classified_issue: ClassifiedIssue) -> Recommendation:
        """Generate a single recommendation, handling retrieval/LLM failures.

        Args:
            classified_issue: The issue to generate a recommendation for.

        Returns:
            The resulting `Recommendation`, either LLM-generated (Step
            4) or a structured fallback if the LLM call fails.
        """
        documents = self._retrieve_documents(classified_issue)
        context = self._build_context(documents)
        prompt = self._prompt_builder.build_recommendation_prompt(
            issue=classified_issue.issue,
            priority=classified_issue.priority,
            category=classified_issue.category,
            context=context,
        )

        try:
            raw_response = self._llm_client.generate(prompt)
            return self._parse_response(raw_response, classified_issue, documents)
        except Exception:  # noqa: BLE001 - Case 2: LLM failure -> structured fallback
            return self._fallback_recommendation(classified_issue, documents)

    # ------------------------------------------------------------------
    # Step 1 + 2: RAG query and retrieval
    # ------------------------------------------------------------------

    def _retrieve_documents(self, classified_issue: ClassifiedIssue) -> list[Document]:
        """Retrieve knowledge documents relevant to a classified issue.

        Case 1 (no retriever available, or retrieval fails) is handled
        by returning an empty list rather than raising — the caller
        then generates a recommendation from the issue information
        alone.

        Args:
            classified_issue: The issue to retrieve documentation for.

        Returns:
            Up to `retrieval_k` retrieved `Document` chunks, or `[]`.
        """
        if not self._retriever.is_initialized:
            return []

        query = self._build_query(classified_issue)
        try:
            return self._retriever.retrieve(
                query,
                k=self._retrieval_k,
                filter={"category": classified_issue.category},
            )
        except Exception:  # noqa: BLE001 - Case 1: no documents -> generate without context
            return []

    @staticmethod
    def _build_query(classified_issue: ClassifiedIssue) -> str:
        """Build the RAG query for a classified issue.

        Combines `category`, `issue`, and `knowledge_topic` — e.g. for
        `{"category": "security", "issue": "Missing Content Security
        Policy", "knowledge_topic": "csp"}` this produces `"security
        Missing Content Security Policy csp implementation"`.

        Args:
            classified_issue: The issue to build a query for.

        Returns:
            The query string to pass to `KnowledgeRetriever.retrieve`.
        """
        return (
            f"{classified_issue.category} {classified_issue.issue} "
            f"{classified_issue.knowledge_topic} implementation"
        )

    @staticmethod
    def _build_context(documents: list[Document]) -> str:
        """Format retrieved documents into the prompt's knowledge context.

        Args:
            documents: Retrieved document chunks, possibly empty.

        Returns:
            A plain-text block combining every chunk's content and
            source, or an empty string if no documents were retrieved
            (in which case `PromptBuilder` substitutes a placeholder).
        """
        if not documents:
            return ""
        return "\n\n".join(
            f"[{document.metadata.get('source', 'unknown')}]\n{document.page_content}"
            for document in documents
        )

    @staticmethod
    def _references_of(documents: list[Document]) -> list[str]:
        """Collect deduplicated knowledge-base source paths from retrieved documents.

        Args:
            documents: Retrieved document chunks, possibly empty.

        Returns:
            Each unique `source` metadata value, in first-seen order.
        """
        seen: set[str] = set()
        references: list[str] = []
        for document in documents:
            source = document.metadata.get("source")
            if source and source not in seen:
                seen.add(source)
                references.append(source)
        return references

    # ------------------------------------------------------------------
    # Step 4: parsing a successful LLM response
    # ------------------------------------------------------------------

    def _parse_response(
        self,
        raw_response: str,
        classified_issue: ClassifiedIssue,
        documents: list[Document],
    ) -> Recommendation:
        """Convert a raw LLM response into a `Recommendation`.

        Args:
            raw_response: The `LLMClient.generate` output, expected to
                follow the `EXPLANATION:` / `RECOMMENDATION:` /
                `IMPLEMENTATION STEPS:` structure `PromptBuilder` asks for.
            classified_issue: The issue this response was generated for.
            documents: The documents retrieved for this issue, used for
                `references`.

        Returns:
            The resulting `Recommendation`, falling back to
            issue-derived text for any section the response omitted.
        """
        sections = self._split_sections(raw_response)

        explanation = sections.get(EXPLANATION_HEADER, "").strip() or classified_issue.reason
        recommendation_text = (
            sections.get(RECOMMENDATION_HEADER, "").strip()
            or f"Address the following issue: {classified_issue.issue}."
        )
        steps = self._parse_steps(sections.get(IMPLEMENTATION_STEPS_HEADER, ""))

        return Recommendation(
            category=classified_issue.category,
            issue=classified_issue.issue,
            priority=classified_issue.priority,
            explanation=explanation,
            recommendation=recommendation_text,
            implementation_steps=steps,
            references=self._references_of(documents),
        )

    @staticmethod
    def _split_sections(raw_response: str) -> dict[str, str]:
        """Split a structured LLM response into its labeled sections.

        Args:
            raw_response: The raw response text.

        Returns:
            A dict mapping each header found in `raw_response` (from
            `EXPLANATION_HEADER`, `RECOMMENDATION_HEADER`,
            `IMPLEMENTATION_STEPS_HEADER`) to the text following it, up
            to the next header or the end of the response.
        """
        headers = (EXPLANATION_HEADER, RECOMMENDATION_HEADER, IMPLEMENTATION_STEPS_HEADER)
        positions = sorted(
            (raw_response.find(header), header)
            for header in headers
            if raw_response.find(header) != -1
        )

        sections: dict[str, str] = {}
        for index, (start_index, header) in enumerate(positions):
            content_start = start_index + len(header)
            content_end = positions[index + 1][0] if index + 1 < len(positions) else len(raw_response)
            sections[header] = raw_response[content_start:content_end].strip()
        return sections

    @staticmethod
    def _parse_steps(steps_text: str) -> list[str]:
        """Extract a bullet list's items from a block of text.

        Args:
            steps_text: Text containing lines starting with `-`.

        Returns:
            Each bullet's text, with the leading `-` removed.
        """
        return [
            line.lstrip("-").strip()
            for line in steps_text.splitlines()
            if line.strip().startswith("-")
        ]

    # ------------------------------------------------------------------
    # Case 2: structured fallback when the LLM call fails
    # ------------------------------------------------------------------

    def _fallback_recommendation(
        self,
        classified_issue: ClassifiedIssue,
        documents: list[Document],
    ) -> Recommendation:
        """Build a structured recommendation without calling the LLM.

        Used when `LLMClient.generate` raises. Grounds the fallback in
        the top retrieved document's own Markdown sections when
        available (its "Purpose", "Implementation Guidelines", and
        "Best Practices" sections), or in the classified issue alone
        if no documents were retrieved.

        Args:
            classified_issue: The issue to generate a fallback for.
            documents: The documents retrieved for this issue, possibly
                empty.

        Returns:
            A fully-populated `Recommendation`, never left blank.
        """
        top_document = documents[0] if documents else None

        explanation = classified_issue.reason
        recommendation_text = f"Address the following issue: {classified_issue.issue}."
        steps: list[str] = []

        if top_document is not None:
            purpose = self._extract_markdown_section(top_document.page_content, "Purpose")
            if purpose:
                explanation = self._first_sentence(purpose) or explanation

            guidelines = self._extract_markdown_section(
                top_document.page_content, "Implementation Guidelines"
            )
            if guidelines:
                recommendation_text = self._first_sentence(guidelines) or recommendation_text

            best_practices = self._extract_markdown_section(
                top_document.page_content, "Best Practices"
            )
            steps = self._extract_bullet_list(best_practices)

        if not steps:
            steps = [f"Consult the '{classified_issue.knowledge_topic}' documentation and apply its guidance."]

        return Recommendation(
            category=classified_issue.category,
            issue=classified_issue.issue,
            priority=classified_issue.priority,
            explanation=explanation,
            recommendation=recommendation_text,
            implementation_steps=steps,
            references=self._references_of(documents),
        )

    @staticmethod
    def _extract_markdown_section(content: str, heading: str) -> Optional[str]:
        """Extract the body text of a `## <heading>` Markdown section.

        Since retrieved content is a chunk (not necessarily the full
        source document), a section may not always be fully present in
        a given chunk; this returns `None` in that case rather than
        raising.

        Args:
            content: The Markdown text to search (typically a single
                retrieved chunk's `page_content`).
            heading: The section heading to find, without `##`.

        Returns:
            The section's body text, or `None` if not found in `content`.
        """
        pattern = rf"##\s+{re.escape(heading)}\s*\n(.*?)(?=\n##\s|\Z)"
        match = re.search(pattern, content, re.DOTALL)
        return match.group(1).strip() if match else None

    @staticmethod
    def _first_sentence(text: str) -> Optional[str]:
        """Extract the first sentence from a block of text.

        Args:
            text: The text to extract from.

        Returns:
            The first sentence (ending in `.`, `!`, or `?`), or the
            whole stripped text if no sentence boundary is found.
        """
        stripped = text.strip()
        match = re.search(r"(.+?[.!?])(\s|$)", stripped, re.DOTALL)
        return match.group(1).strip() if match else stripped or None

    @staticmethod
    def _extract_bullet_list(text: Optional[str]) -> list[str]:
        """Extract a Markdown bullet list's items from a section's body text.

        Args:
            text: The section body text, or `None`.

        Returns:
            Each bullet's text, or `[]` if `text` is `None` or contains
            no bullet lines.
        """
        if not text:
            return []
        return [line.lstrip("-").strip() for line in text.splitlines() if line.strip().startswith("-")]

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    @staticmethod
    def _summarize(recommendations: list[Recommendation]) -> dict[str, int]:
        """Count generated recommendations per priority level.

        Args:
            recommendations: Every recommendation generated by `generate`.

        Returns:
            A dict with `"HIGH"`, `"MEDIUM"`, and `"LOW"` keys, always
            present (even at 0), mapped to their respective counts.
        """
        summary = {priority: 0 for priority in _PRIORITY_LEVELS}
        for recommendation in recommendations:
            summary[recommendation.priority] = summary.get(recommendation.priority, 0) + 1
        return summary

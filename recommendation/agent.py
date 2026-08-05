"""Recommendation Agent.

This module is the final analysis layer of ARAS. It turns each
`ClassifiedIssue` produced by the Rule Engine into a professional,
actionable `Recommendation`, by retrieving grounding documentation from
the RAG knowledge base (`ARASRetriever`: metadata filter + bi-encoder +
cross-encoder re-rank) and asking an `LLMClient` to expand it into an
explanation, impact, recommendation, implementation steps, best
practices, expected benefits, and references.

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
orchestrates already-built components: `ARASRetriever`, `PromptBuilder`,
and `LLMClient`.
"""

from __future__ import annotations

import re
from typing import Optional

from langchain_core.documents import Document

from models.recommendation import Recommendation, RecommendationResult
from models.rule_engine import ClassifiedIssue
from recommendation.llm_client import GroqLLMClient, LLMClient
from recommendation.prompt_builder import (
    BEST_PRACTICES_HEADER,
    EXPECTED_BENEFITS_HEADER,
    EXPLANATION_HEADER,
    IMPACT_HEADER,
    IMPLEMENTATION_STEPS_HEADER,
    RECOMMENDATION_HEADER,
    RESPONSE_HEADERS,
    PromptBuilder,
)
from recommendation.rag.retriever import ARASRetriever

_PRIORITY_LEVELS = ("HIGH", "MEDIUM", "LOW")
_PRIORITY_RANK = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}

# Criteria that are technically distinct (different evaluation logic, kept
# separate in RuleEngineResult/scoring/retrieval) but read as the same
# real-world fix to a report reader — merged for recommendation purposes
# only. `discoverability/api_discoverability` ("is any API surface visible
# at all") and `interaction/api_documentation` ("is there formal API
# documentation") both resolve to "publish OpenAPI/Swagger docs" in
# practice, since they inspect overlapping evidence and almost always
# fail together. Maps a criterion to the canonical criterion its merge
# group is keyed by; a criterion absent from this table is its own group.
_CRITERION_MERGE_GROUPS: dict[str, str] = {
    "api_discoverability": "api_documentation",
}

_MISSING_KNOWLEDGE_NOTE = (
    " No specific ARAS knowledge base documentation was retrieved for this "
    "issue; this recommendation is based on general best practices only."
)
_GENERATION_FAILED_EXPLANATION = (
    "Automated recommendation generation is temporarily unavailable for this "
    "issue. The details below are a structured fallback derived directly "
    "from the Rule Engine's own classification, not from the LLM."
)


class RecommendationAgent:
    """Generates a professional recommendation for every classified issue.

    This class holds no retrieval, embedding, vector-storage, or
    priority-classification logic of its own — it delegates entirely
    to an already-built `ARASRetriever`, `PromptBuilder`, and
    `LLMClient`, and only orchestrates the flow between them:

        ClassifiedIssue -> ARASRetriever.retrieve() -> Documents
                         -> PromptBuilder.build() -> prompt
                         -> LLMClient.invoke() -> raw response
                         -> Recommendation
    """

    def __init__(
        self,
        retriever: Optional[ARASRetriever] = None,
        prompt_builder: Optional[PromptBuilder] = None,
        llm_client: Optional[LLMClient] = None,
    ) -> None:
        """Configure the Recommendation Agent's collaborators.

        Args:
            retriever: An `ARASRetriever`, ideally already initialized
                via `retriever.initialize(vector_store_path)`. If
                omitted, an uninitialized `ARASRetriever` is used,
                which causes every issue to fall back to generation
                without retrieved documentation (see
                `_retrieve_documents`) — retrieval failure is handled
                gracefully, not treated as fatal.
            prompt_builder: The prompt builder to use. A default
                `PromptBuilder` is created if omitted.
            llm_client: The LLM backend to use. Defaults to
                `GroqLLMClient` (LangChain + Groq, requires
                `GROQ_API_KEY`), and can be swapped for any other
                `LLMClient` implementation — e.g. `TemplateLLMClient`
                for offline tests — without changing this class.
        """
        self._retriever = retriever or ARASRetriever()
        self._prompt_builder = prompt_builder or PromptBuilder()
        self._llm_client = llm_client or GroqLLMClient()

    def generate(self, classified_issues: list[ClassifiedIssue]) -> RecommendationResult:
        """Generate a recommendation for every classified issue.

        Issues sharing the same `criterion` (e.g. `open_graph`,
        independently checked by both `DiscoverabilityAgent` and
        `ComprehensionAgent` against the exact same evidence) are
        merged into a single representative issue first — see
        `_merge_duplicate_criteria` — so the reader gets one grounded
        recommendation per real technical gap instead of two
        near-identical ones differing only in category/priority. The
        Rule Engine's own output (`RuleEngineResult.issues`/`summary`,
        each dimension's own score) is never touched by this merge —
        it only affects which issues are handed to the LLM here.

        Args:
            classified_issues: The Rule Engine's output — one
                `ClassifiedIssue` per detected readiness gap.

        Returns:
            A `RecommendationResult` with one `Recommendation` per
            merged issue and a priority-level summary count.
        """
        merged_issues = self._merge_duplicate_criteria(classified_issues)
        recommendations = [self._generate_one(issue) for issue in merged_issues]
        return RecommendationResult(
            recommendations=recommendations,
            summary=self._summarize(recommendations),
        )

    # ------------------------------------------------------------------
    # Merging issues that share the same criterion
    # ------------------------------------------------------------------

    @staticmethod
    def _merge_duplicate_criteria(classified_issues: list[ClassifiedIssue]) -> list[ClassifiedIssue]:
        """Merge issues that share the same `criterion` into one representative issue.

        Grouping is by `criterion` only (not by issue text or
        category), since `criterion` is the ARAS-canonical identity of
        "which technical gap is this" — two issues with the same
        criterion are, by definition, the same underlying gap reported
        by more than one analysis agent. An issue with an empty
        `criterion` (e.g. a hand-built test double that omits it) is
        never merged with anything else, to avoid accidentally
        collapsing unrelated issues that all happen to default to "".
        Grouping key is `_CRITERION_MERGE_GROUPS.get(criterion,
        criterion)`, so criteria that are technically distinct but
        represent the same real-world fix (see that table) are merged
        too, not just byte-identical criteria.

        Args:
            classified_issues: The Rule Engine's raw output.

        Returns:
            One issue per distinct merge group, in first-seen order;
            single-issue groups are returned unchanged.
        """
        groups: dict[str, list[ClassifiedIssue]] = {}
        order: list[str] = []
        for index, issue in enumerate(classified_issues):
            if issue.criterion:
                key = _CRITERION_MERGE_GROUPS.get(issue.criterion, issue.criterion)
            else:
                key = f"__no_criterion_{index}"
            if key not in groups:
                groups[key] = []
                order.append(key)
            groups[key].append(issue)

        return [
            groups[key][0] if len(groups[key]) == 1 else RecommendationAgent._combine(groups[key])
            for key in order
        ]

    @staticmethod
    def _combine(group: list[ClassifiedIssue]) -> ClassifiedIssue:
        """Combine several same-group issues into one representative issue.

        The representative issue's own message is used as-is (a single,
        clean sentence) rather than concatenating every member's
        wording — a reader should see one clear statement of the gap,
        not "message A / message B". Everything else (evidence,
        affected categories) is still merged, just not surfaced as the
        headline text.

        Args:
            group: Two or more `ClassifiedIssue`s in the same merge group.

        Returns:
            A single `ClassifiedIssue`: highest priority in the group,
            its own issue message, every distinct category combined,
            and evidence merged from every member — used only to drive
            recommendation generation, never fed back into
            `RuleEngineResult`.
        """
        primary = min(group, key=lambda issue: _PRIORITY_RANK.get(issue.priority, len(_PRIORITY_RANK)))
        categories = sorted({issue.category for issue in group})
        combined_evidence: dict = {}
        for issue in group:
            combined_evidence.update(issue.evidence)

        return ClassifiedIssue(
            category=", ".join(categories),
            issue=primary.issue,
            priority=primary.priority,
            knowledge_topic=primary.knowledge_topic,
            reason=primary.reason,
            criterion=primary.criterion,
            score=primary.score,
            evidence=combined_evidence,
            retrieval_query={"category": primary.category, "criterion": primary.criterion},
            metadata=primary.metadata,
        )

    # ------------------------------------------------------------------
    # Per-issue generation
    # ------------------------------------------------------------------

    def _generate_one(self, classified_issue: ClassifiedIssue) -> Recommendation:
        """Generate a single recommendation, handling retrieval/LLM failures.

        Args:
            classified_issue: The issue to generate a recommendation for.

        Returns:
            The resulting `Recommendation`, either LLM-generated or a
            structured fallback if the LLM call fails. Never raises —
            a single issue's generation failure never aborts the rest
            of the ARAS workflow.
        """
        documents = self._retrieve_documents(classified_issue)
        prompt = self._prompt_builder.build(classified_issue, documents)

        try:
            raw_response = self._llm_client.invoke(prompt)
            return self._parse_response(raw_response, classified_issue, documents)
        except Exception:  # noqa: BLE001 - LLM failure -> structured fallback, don't crash
            return self._fallback_recommendation(classified_issue, documents)

    # ------------------------------------------------------------------
    # Step 1: retrieval
    # ------------------------------------------------------------------

    def _retrieve_documents(self, classified_issue: ClassifiedIssue) -> list[Document]:
        """Retrieve knowledge documents relevant to a classified issue.

        No documents available (retriever not initialized, retrieval
        raises, or nothing matched) is handled by returning an empty
        list rather than raising — the caller then generates a
        recommendation from the issue information alone, and
        `PromptBuilder` substitutes a "no knowledge retrieved"
        placeholder so this degradation is visible in the prompt
        itself, not silently hidden.

        Args:
            classified_issue: The issue to retrieve documentation for.

        Returns:
            The `Document` chunks `ARASRetriever.retrieve` returns for
            this issue, or `[]`.
        """
        if not self._retriever.is_initialized:
            return []

        try:
            return self._retriever.retrieve(classified_issue.to_dict())
        except Exception:  # noqa: BLE001 - no documents -> generate without context
            return []

    @staticmethod
    def _references_of(documents: list[Document]) -> list[str]:
        """Collect deduplicated knowledge-base source paths from retrieved documents.

        Always derived from the documents actually retrieved, never
        from LLM-generated text, so a recommendation can never cite a
        source it wasn't really grounded in.

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
            raw_response: The `LLMClient.invoke` output, expected to
                follow the `PromptBuilder.RESPONSE_HEADERS` structure.
            classified_issue: The issue this response was generated for.
            documents: The documents retrieved for this issue, used for
                `references` (never for LLM-claimed references — see
                `_references_of`).

        Returns:
            The resulting `Recommendation`, falling back to
            issue-derived text for any section the response omitted.
        """
        sections = self._split_sections(raw_response)
        missing_knowledge_suffix = _MISSING_KNOWLEDGE_NOTE if not documents else ""

        explanation = (
            sections.get(EXPLANATION_HEADER, "").strip() or classified_issue.reason
        ) + missing_knowledge_suffix
        impact = sections.get(IMPACT_HEADER, "").strip() or (
            f"Leaving this issue unaddressed reduces the {classified_issue.category} "
            "dimension's Agentic Readiness score."
        )
        recommendation_text = (
            sections.get(RECOMMENDATION_HEADER, "").strip()
            or f"Address the following issue: {classified_issue.issue}."
        )
        steps = self._parse_bullets(sections.get(IMPLEMENTATION_STEPS_HEADER, ""))
        best_practices = self._parse_bullets(sections.get(BEST_PRACTICES_HEADER, ""))
        expected_benefits = sections.get(EXPECTED_BENEFITS_HEADER, "").strip()

        return Recommendation(
            category=classified_issue.category,
            criterion=classified_issue.criterion,
            issue=classified_issue.issue,
            priority=classified_issue.priority,
            explanation=explanation,
            impact=impact,
            recommendation=recommendation_text,
            implementation_steps=steps,
            best_practices=best_practices,
            expected_benefits=expected_benefits,
            references=self._references_of(documents),
        )

    @staticmethod
    def _split_sections(raw_response: str) -> dict[str, str]:
        """Split a structured LLM response into its labeled sections.

        Args:
            raw_response: The raw response text.

        Returns:
            A dict mapping each header found in `raw_response` (from
            `PromptBuilder.RESPONSE_HEADERS`) to the text following it,
            up to the next header or the end of the response.
        """
        positions = sorted(
            (raw_response.find(header), header)
            for header in RESPONSE_HEADERS
            if raw_response.find(header) != -1
        )

        sections: dict[str, str] = {}
        for index, (start_index, header) in enumerate(positions):
            content_start = start_index + len(header)
            content_end = positions[index + 1][0] if index + 1 < len(positions) else len(raw_response)
            sections[header] = raw_response[content_start:content_end].strip()
        return sections

    @staticmethod
    def _parse_bullets(text: str) -> list[str]:
        """Extract a bullet list's items from a block of text.

        Args:
            text: Text containing lines starting with `-`.

        Returns:
            Each bullet's text, with the leading `-` removed.
        """
        return [
            line.lstrip("-").strip()
            for line in text.splitlines()
            if line.strip().startswith("-")
        ]

    # ------------------------------------------------------------------
    # LLM failure: structured fallback (error state, never a crash)
    # ------------------------------------------------------------------

    def _fallback_recommendation(
        self,
        classified_issue: ClassifiedIssue,
        documents: list[Document],
    ) -> Recommendation:
        """Build a structured recommendation without calling the LLM.

        Used when `LLMClient.invoke` raises. Grounds the fallback in
        the top retrieved document's own Markdown sections when
        available (its "Common Issues" and "Recommendation Strategy"
        sections, per the ARAS knowledge base template), or in the
        classified issue alone if no documents were retrieved. This is
        an explicit error state — never a workflow crash.

        Args:
            classified_issue: The issue to generate a fallback for.
            documents: The documents retrieved for this issue, possibly
                empty.

        Returns:
            A fully-populated `Recommendation`, never left blank.
        """
        top_document = documents[0] if documents else None

        explanation = f"{_GENERATION_FAILED_EXPLANATION} Reason: {classified_issue.reason}"
        impact = (
            f"Leaving this issue unaddressed reduces the {classified_issue.category} "
            "dimension's Agentic Readiness score."
        )
        recommendation_text = f"Address the following issue: {classified_issue.issue}."
        steps: list[str] = []
        best_practices: list[str] = []

        if top_document is not None:
            recommendation_strategy = self._extract_markdown_section(
                top_document.page_content, "Recommendation Strategy"
            )
            if recommendation_strategy:
                recommendation_text = self._first_sentence(recommendation_strategy) or recommendation_text

            steps = self._extract_bullet_list(
                self._extract_markdown_section(top_document.page_content, "Implementation Guidance")
            )
            best_practices = self._extract_bullet_list(
                self._extract_markdown_section(top_document.page_content, "Validation Checklist")
            )

        if not steps:
            steps = [f"Consult the '{classified_issue.criterion}' documentation and apply its guidance."]

        return Recommendation(
            category=classified_issue.category,
            criterion=classified_issue.criterion,
            issue=classified_issue.issue,
            priority=classified_issue.priority,
            explanation=explanation,
            impact=impact,
            recommendation=recommendation_text,
            implementation_steps=steps,
            best_practices=best_practices,
            expected_benefits="",
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

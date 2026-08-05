"""Prompt construction for the ARAS Recommendation Agent.

This module builds the exact text prompt sent to an `LLMClient`. It
has no knowledge of the Rule Engine's classification logic, the
Retriever's search logic, ChromaDB, or any LLM backend — it only
formats already-resolved data (a `ClassifiedIssue` and its retrieved
`Document` chunks) into a single prompt string with a fixed, parseable
output contract.

This module MUST NOT:
    - retrieve documents
    - call any LLM
    - classify issues or assign priorities
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langchain_core.documents import Document

    from models.rule_engine import ClassifiedIssue

# Section headers the prompt asks the LLM to reproduce verbatim in its
# response, so `RecommendationAgent` can parse the response back into
# structured `Recommendation` fields regardless of which `LLMClient`
# implementation produced it.
EXPLANATION_HEADER = "EXPLANATION:"
IMPACT_HEADER = "IMPACT:"
RECOMMENDATION_HEADER = "RECOMMENDATION:"
IMPLEMENTATION_STEPS_HEADER = "IMPLEMENTATION STEPS:"
BEST_PRACTICES_HEADER = "BEST PRACTICES:"
EXPECTED_BENEFITS_HEADER = "EXPECTED BENEFITS:"
REFERENCES_HEADER = "REFERENCES:"

# The order every generated response is asked to follow; also the
# order `RecommendationAgent` looks for these headers in when parsing.
RESPONSE_HEADERS = (
    EXPLANATION_HEADER,
    IMPACT_HEADER,
    RECOMMENDATION_HEADER,
    IMPLEMENTATION_STEPS_HEADER,
    BEST_PRACTICES_HEADER,
    EXPECTED_BENEFITS_HEADER,
    REFERENCES_HEADER,
)

_SYSTEM_ROLE = (
    "You are an expert in AI Agent Readiness Assessment (ARAS).\n"
    "Generate accurate, professional technical recommendations that help a "
    "website become more discoverable, comprehensible, and interactable by "
    "autonomous AI agents.\n"
    "Use only the provided knowledge context and the issue's own evidence. "
    "Do not hallucinate standards, headers, or technical details that are "
    "not grounded in the retrieved knowledge or well-established, widely "
    "known web/security best practices."
)

_NO_KNOWLEDGE_PLACEHOLDER = (
    "No specific technical documentation was retrieved for this issue. "
    "Base the recommendation on general best practices for this category."
)

_GENERATION_INSTRUCTIONS = (
    "Instruction:\n"
    "Generate a professional recommendation for an AI agent readiness "
    "audit, grounded in the retrieved knowledge above. Respond using "
    "exactly this structure, with no extra commentary before or after "
    "it:\n\n"
    f"{EXPLANATION_HEADER}\n"
    "<one or two sentences explaining why this issue matters>\n\n"
    f"{IMPACT_HEADER}\n"
    "<one or two sentences on the consequence of leaving this unaddressed>\n\n"
    f"{RECOMMENDATION_HEADER}\n"
    "<one clear, actionable sentence>\n\n"
    f"{IMPLEMENTATION_STEPS_HEADER}\n"
    "- <first concrete step>\n"
    "- <second concrete step>\n"
    "- <third concrete step>\n\n"
    f"{BEST_PRACTICES_HEADER}\n"
    "- <first best practice>\n"
    "- <second best practice>\n\n"
    f"{EXPECTED_BENEFITS_HEADER}\n"
    "<one or two sentences on the benefit of implementing this recommendation>\n\n"
    f"{REFERENCES_HEADER}\n"
    "- <name or standard referenced from the knowledge context above, if any>\n"
)


class PromptBuilder:
    """Builds LLM prompts for generating a single issue's recommendation.

    This class holds no retrieval or generation logic. It is a pure
    string-formatting step: a `ClassifiedIssue` and its retrieved
    `Document` chunks in, one prompt string out.
    """

    def build(self, context: "ClassifiedIssue", documents: list["Document"]) -> str:
        """Build the prompt for generating a recommendation for one issue.

        Args:
            context: The Rule Engine's classified issue — supplies the
                ISSUE CONTEXT section (`category`, `criterion`,
                `priority`, `issue`, `evidence`).
            documents: The knowledge chunks retrieved for `context` by
                the RAG Retriever, possibly empty. Supplies the
                RETRIEVED KNOWLEDGE section; a placeholder note is
                substituted automatically when empty.

        Returns:
            The complete prompt string: SYSTEM ROLE, ISSUE CONTEXT,
            RETRIEVED KNOWLEDGE, then GENERATION INSTRUCTIONS asking
            for the `RESPONSE_HEADERS` structure.
        """
        return (
            f"{_SYSTEM_ROLE}\n\n"
            f"{self._build_issue_context(context)}\n\n"
            f"{self._build_retrieved_knowledge(documents)}\n\n"
            f"{_GENERATION_INSTRUCTIONS}"
        )

    @staticmethod
    def _build_issue_context(context: "ClassifiedIssue") -> str:
        """Format a `ClassifiedIssue` into the prompt's ISSUE CONTEXT section.

        Args:
            context: The classified issue to format.

        Returns:
            The ISSUE CONTEXT section text.
        """
        return (
            "ISSUE CONTEXT\n"
            f"Category: {context.category}\n"
            f"Criterion: {context.criterion}\n"
            f"Priority: {context.priority}\n"
            f"Issue: {context.issue}\n"
            f"Evidence: {context.evidence or '(none available)'}"
        )

    @classmethod
    def _build_retrieved_knowledge(cls, documents: list["Document"]) -> str:
        """Format retrieved documents into the prompt's RETRIEVED KNOWLEDGE section.

        Each document is listed with its `source`, `criterion`, and
        `category` metadata preserved and visible, so the LLM (and a
        human reviewing the prompt) can tell exactly which knowledge
        document backs which content.

        Args:
            documents: Retrieved document chunks, possibly empty.

        Returns:
            The RETRIEVED KNOWLEDGE section text, or a placeholder note
            if `documents` is empty.
        """
        if not documents:
            return f"RETRIEVED KNOWLEDGE\n{_NO_KNOWLEDGE_PLACEHOLDER}"

        entries = [
            cls._format_document(index, document) for index, document in enumerate(documents, start=1)
        ]
        return "RETRIEVED KNOWLEDGE\n" + "\n\n".join(entries)

    @staticmethod
    def _format_document(index: int, document: "Document") -> str:
        """Format a single retrieved document for the RETRIEVED KNOWLEDGE section.

        Args:
            index: The document's 1-based position in the retrieved list.
            document: The retrieved document chunk.

        Returns:
            A `[index] Source: ... | Criterion: ... | Category: ...`
            header followed by the document's own text.
        """
        metadata = document.metadata
        header = (
            f"[{index}] Source: {metadata.get('source', 'unknown')} | "
            f"Criterion: {metadata.get('criterion', 'unknown')} | "
            f"Category: {metadata.get('category', 'unknown')}"
        )
        return f"{header}\n{document.page_content}"

"""Prompt construction for the ARAS Recommendation Agent.

This module builds the exact text prompt sent to an `LLMClient`. It
has no knowledge of the Rule Engine, the Retriever, ChromaDB, or any
LLM backend — it only formats already-resolved strings (issue,
priority, category, retrieved-knowledge context) into a single prompt
string with a fixed, parseable output contract.

This module MUST NOT:
    - retrieve documents
    - call any LLM
    - classify issues or assign priorities
"""

from __future__ import annotations

# Section headers the prompt asks the LLM to reproduce verbatim in its
# response, so `RecommendationAgent` can parse the response back into
# structured fields regardless of which `LLMClient` implementation
# produced it.
EXPLANATION_HEADER = "EXPLANATION:"
RECOMMENDATION_HEADER = "RECOMMENDATION:"
IMPLEMENTATION_STEPS_HEADER = "IMPLEMENTATION STEPS:"

_NO_CONTEXT_PLACEHOLDER = (
    "No specific technical documentation was retrieved for this issue. "
    "Base the recommendation on general best practices for this category."
)


class PromptBuilder:
    """Builds LLM prompts for generating a single issue's recommendation.

    This class holds no retrieval or generation logic. It is a pure
    string-formatting step: structured inputs in, one prompt string out.
    """

    def build_recommendation_prompt(
        self,
        issue: str,
        priority: str,
        category: str,
        context: str,
    ) -> str:
        """Build the prompt for generating a recommendation for one issue.

        Args:
            issue: The issue message to generate a recommendation for.
            priority: The issue's deterministic priority (`"HIGH"`,
                `"MEDIUM"`, or `"LOW"`), as assigned by the Rule Engine.
            category: The ARAS dimension the issue belongs to.
            context: Retrieved knowledge-base text relevant to the
                issue, already formatted as plain text (e.g. by joining
                retrieved `Document.page_content` values). Pass an
                empty string if no documents were retrieved — a
                placeholder note is substituted automatically.

        Returns:
            The complete prompt string, instructing the LLM to respond
            using the `EXPLANATION_HEADER` / `RECOMMENDATION_HEADER` /
            `IMPLEMENTATION_STEPS_HEADER` structure this module defines.
        """
        knowledge_section = context.strip() if context.strip() else _NO_CONTEXT_PLACEHOLDER

        return (
            "You are a technical assistant for the Agentic Readiness Assessment "
            "System (ARAS). Generate a professional, actionable recommendation "
            "for the following website issue.\n\n"
            f"Website issue: {issue}\n"
            f"Category: {category}\n"
            f"Priority: {priority}\n"
            f"Technical knowledge:\n{knowledge_section}\n\n"
            "Instruction:\n"
            "Generate a professional recommendation for an AI agent readiness "
            "audit. Respond using exactly this structure, with no extra "
            "commentary before or after it:\n\n"
            f"{EXPLANATION_HEADER}\n"
            "<one or two sentences explaining why this issue matters>\n\n"
            f"{RECOMMENDATION_HEADER}\n"
            "<one clear, actionable sentence>\n\n"
            f"{IMPLEMENTATION_STEPS_HEADER}\n"
            "- <first concrete step>\n"
            "- <second concrete step>\n"
            "- <third concrete step>\n"
        )

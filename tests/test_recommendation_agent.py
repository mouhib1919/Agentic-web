"""Unit tests for :class:`RecommendationAgent`.

Exercises the full Retriever -> PromptBuilder -> LLMClient ->
Recommendation orchestration using lightweight, dependency-injected
test doubles (`_FakeRetriever`, `_FailingLLMClient`) and the real,
deterministic `TemplateLLMClient` — no network access, ChromaDB, or
GROQ_API_KEY required. `RecommendationAgent` itself is exercised
unmodified; only its collaborators are swapped for test doubles, the
same pattern `RecommendationAgent.__init__` is designed to support.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running this file directly (e.g. from an IDE "Run" button) by
# ensuring the project root is importable, not just the `tests/` folder.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_core.documents import Document

from models.rule_engine import ClassifiedIssue
from recommendation.agent import RecommendationAgent
from recommendation.llm_client import LLMClient, TemplateLLMClient
from recommendation.prompt_builder import PromptBuilder


class _FakeRetriever:
    """Test double for `ARASRetriever`: returns canned documents, records calls.

    `RecommendationAgent` only depends on `is_initialized` and
    `retrieve(context)` — this double implements exactly that surface,
    so no real ChromaDB collection or embedding/cross-encoder model is
    needed to test the agent's own orchestration logic.
    """

    def __init__(self, documents: list[Document]) -> None:
        self.is_initialized = True
        self._documents = documents
        self.calls: list[dict] = []

    def retrieve(self, context: dict) -> list[Document]:
        self.calls.append(context)
        return self._documents


class _FailingLLMClient(LLMClient):
    """Test double simulating an LLM call that always raises."""

    def invoke(self, prompt: str) -> str:
        raise RuntimeError("simulated LLM outage")


def _csp_issue() -> ClassifiedIssue:
    """Build a realistic CSP `ClassifiedIssue`, as the Rule Engine would produce."""
    return ClassifiedIssue(
        category="security",
        issue="Missing Content-Security-Policy header.",
        priority="HIGH",
        knowledge_topic="csp",
        reason="Missing CSP leaves the site open to script injection and XSS attacks.",
        criterion="csp",
        score=71.43,
        evidence={"csp": False},
        retrieval_query={"category": "security", "criterion": "csp"},
    )


def _csp_documents() -> list[Document]:
    """Build canned retrieved documents for the CSP criterion."""
    return [
        Document(
            page_content=(
                "# Content Security Policy (CSP)\n\n"
                "## Recommendation Strategy\n"
                "Configure a strict Content-Security-Policy header on every response.\n\n"
                "## Implementation Guidance\n"
                "- Add the Content-Security-Policy header at the reverse proxy or app layer.\n"
                "- Start with a report-only policy before enforcing it.\n\n"
                "## Validation Checklist\n"
                "- Confirm the header is present on the homepage response.\n"
                "- Confirm no console CSP violations appear during normal use.\n"
            ),
            metadata={"source": "aras_knowledge/security/csp.md", "criterion": "csp", "category": "security"},
        )
    ]


def _print_recommendation(label: str, recommendation) -> None:
    print(f"--- {label} ---")
    print(f"Category: {recommendation.category}")
    print(f"Criterion: {recommendation.criterion}")
    print(f"Priority: {recommendation.priority}")
    print(f"Explanation: {recommendation.explanation}")
    print(f"Impact: {recommendation.impact}")
    print(f"Recommendation: {recommendation.recommendation}")
    print(f"Implementation steps: {recommendation.implementation_steps}")
    print(f"Best practices: {recommendation.best_practices}")
    print(f"Expected benefits: {recommendation.expected_benefits}")
    print(f"References: {recommendation.references}")
    print()


# ---------------------------------------------------------------------------
# Test 1: CSP missing issue -> retriever called, prompt generated, LLM
# called, RecommendationResult returned.
# ---------------------------------------------------------------------------


def test_csp_issue_produces_a_full_recommendation() -> None:
    retriever = _FakeRetriever(_csp_documents())
    agent = RecommendationAgent(
        retriever=retriever,
        prompt_builder=PromptBuilder(),
        llm_client=TemplateLLMClient(),
    )

    result = agent.generate([_csp_issue()])
    _print_recommendation("csp issue", result.recommendations[0])

    # Retriever was called with the issue's own context.
    assert len(retriever.calls) == 1
    assert retriever.calls[0]["category"] == "security"
    assert retriever.calls[0]["criterion"] == "csp"

    assert len(result.recommendations) == 1
    recommendation = result.recommendations[0]
    assert recommendation.category == "security"
    assert recommendation.criterion == "csp"
    assert recommendation.priority == "HIGH"
    assert recommendation.issue == "Missing Content-Security-Policy header."
    assert recommendation.explanation
    assert recommendation.impact
    assert recommendation.recommendation
    assert recommendation.implementation_steps
    assert recommendation.best_practices
    assert recommendation.references == ["aras_knowledge/security/csp.md"]
    assert result.summary == {"HIGH": 1, "MEDIUM": 0, "LOW": 0}


# ---------------------------------------------------------------------------
# Test 2: no retrieved documents -> graceful handling, no crash.
# ---------------------------------------------------------------------------


def test_no_retrieved_documents_is_handled_gracefully() -> None:
    retriever = _FakeRetriever(documents=[])
    agent = RecommendationAgent(
        retriever=retriever,
        prompt_builder=PromptBuilder(),
        llm_client=TemplateLLMClient(),
    )

    result = agent.generate([_csp_issue()])
    _print_recommendation("no documents", result.recommendations[0])

    recommendation = result.recommendations[0]
    assert recommendation.references == []
    assert recommendation.recommendation
    assert "No specific ARAS knowledge base documentation was retrieved" in recommendation.explanation


def test_uninitialized_retriever_is_handled_gracefully() -> None:
    """An uninitialized retriever (no vector store yet) never crashes generation."""

    class _UninitializedRetriever:
        is_initialized = False

    agent = RecommendationAgent(
        retriever=_UninitializedRetriever(),  # type: ignore[arg-type]
        prompt_builder=PromptBuilder(),
        llm_client=TemplateLLMClient(),
    )

    result = agent.generate([_csp_issue()])

    assert len(result.recommendations) == 1
    assert result.recommendations[0].references == []


# ---------------------------------------------------------------------------
# Test 3: a mocked LLM response is correctly transformed into a Recommendation.
# ---------------------------------------------------------------------------


class _CannedLLMClient(LLMClient):
    """Returns a fixed, hand-written response to verify response parsing."""

    def invoke(self, prompt: str) -> str:
        return (
            "EXPLANATION:\n"
            "Missing CSP allows arbitrary script injection.\n\n"
            "IMPACT:\n"
            "Attackers can execute arbitrary JavaScript in visitors' browsers.\n\n"
            "RECOMMENDATION:\n"
            "Deploy a strict Content-Security-Policy header.\n\n"
            "IMPLEMENTATION STEPS:\n"
            "- Add the header at the CDN or reverse proxy layer.\n"
            "- Start in report-only mode for one week.\n"
            "- Switch to enforcing mode once no violations are reported.\n\n"
            "BEST PRACTICES:\n"
            "- Avoid 'unsafe-inline' and 'unsafe-eval' directives.\n"
            "- Use a nonce or hash for any required inline scripts.\n\n"
            "EXPECTED BENEFITS:\n"
            "Significantly reduces the site's exposure to XSS attacks.\n\n"
            "REFERENCES:\n"
            "- W3C Content Security Policy Level 3\n"
        )


def test_mocked_llm_response_is_parsed_into_recommendation_fields() -> None:
    retriever = _FakeRetriever(_csp_documents())
    agent = RecommendationAgent(
        retriever=retriever,
        prompt_builder=PromptBuilder(),
        llm_client=_CannedLLMClient(),
    )

    result = agent.generate([_csp_issue()])
    _print_recommendation("mocked llm response", result.recommendations[0])

    recommendation = result.recommendations[0]
    assert recommendation.explanation == "Missing CSP allows arbitrary script injection."
    assert recommendation.impact == "Attackers can execute arbitrary JavaScript in visitors' browsers."
    assert recommendation.recommendation == "Deploy a strict Content-Security-Policy header."
    assert recommendation.implementation_steps == [
        "Add the header at the CDN or reverse proxy layer.",
        "Start in report-only mode for one week.",
        "Switch to enforcing mode once no violations are reported.",
    ]
    assert recommendation.best_practices == [
        "Avoid 'unsafe-inline' and 'unsafe-eval' directives.",
        "Use a nonce or hash for any required inline scripts.",
    ]
    assert recommendation.expected_benefits == "Significantly reduces the site's exposure to XSS attacks."
    # References always come from retrieved document metadata, never from
    # the LLM's own REFERENCES section (which is not parsed into this field).
    assert recommendation.references == ["aras_knowledge/security/csp.md"]


# ---------------------------------------------------------------------------
# LLM failure: an explicit, structured error state, not a crash.
# ---------------------------------------------------------------------------


def test_llm_failure_falls_back_to_a_structured_recommendation() -> None:
    retriever = _FakeRetriever(_csp_documents())
    agent = RecommendationAgent(
        retriever=retriever,
        prompt_builder=PromptBuilder(),
        llm_client=_FailingLLMClient(),
    )

    result = agent.generate([_csp_issue()])
    _print_recommendation("llm failure fallback", result.recommendations[0])

    recommendation = result.recommendations[0]
    assert "temporarily unavailable" in recommendation.explanation
    assert recommendation.recommendation
    assert recommendation.implementation_steps
    assert recommendation.references == ["aras_knowledge/security/csp.md"]


def test_llm_failure_with_no_documents_still_returns_a_recommendation() -> None:
    retriever = _FakeRetriever(documents=[])
    agent = RecommendationAgent(
        retriever=retriever,
        prompt_builder=PromptBuilder(),
        llm_client=_FailingLLMClient(),
    )

    result = agent.generate([_csp_issue()])

    recommendation = result.recommendations[0]
    assert recommendation.references == []
    assert recommendation.implementation_steps  # generic fallback step, never empty


# ---------------------------------------------------------------------------
# Multiple issues -> priority summary.
# ---------------------------------------------------------------------------


def test_summary_counts_recommendations_per_priority() -> None:
    retriever = _FakeRetriever(_csp_documents())
    agent = RecommendationAgent(
        retriever=retriever,
        prompt_builder=PromptBuilder(),
        llm_client=TemplateLLMClient(),
    )

    medium_issue = ClassifiedIssue(
        category="discoverability",
        issue="No sitemap.xml found",
        priority="MEDIUM",
        knowledge_topic="sitemap",
        reason="Missing sitemap.xml slows down content discovery for crawlers and agents.",
        criterion="sitemap",
        score=57.14,
        evidence={"sitemap": False},
        retrieval_query={"category": "discoverability", "criterion": "sitemap"},
    )

    result = agent.generate([_csp_issue(), medium_issue])

    assert len(result.recommendations) == 2
    assert result.summary == {"HIGH": 1, "MEDIUM": 1, "LOW": 0}


# ---------------------------------------------------------------------------
# Same-criterion issues (e.g. open_graph, checked identically by both
# DiscoverabilityAgent and ComprehensionAgent) are merged into one
# recommendation instead of two near-identical ones.
# ---------------------------------------------------------------------------


def _open_graph_issue(category: str, issue_text: str, priority: str) -> ClassifiedIssue:
    return ClassifiedIssue(
        category=category,
        issue=issue_text,
        priority=priority,
        knowledge_topic="open_graph",
        reason=f"Missing Open Graph metadata is a {priority.lower()}-impact {category} gap.",
        criterion="open_graph",
        score=42.0,
        evidence={"open_graph": False},
        retrieval_query={"category": category, "criterion": "open_graph"},
    )


def test_same_criterion_issues_are_merged_into_one_recommendation() -> None:
    retriever = _FakeRetriever(documents=[])
    agent = RecommendationAgent(
        retriever=retriever,
        prompt_builder=PromptBuilder(),
        llm_client=TemplateLLMClient(),
    )

    discoverability_issue = _open_graph_issue(
        "discoverability", "No Open Graph metadata found", "MEDIUM"
    )
    comprehension_issue = _open_graph_issue(
        "comprehension", "Missing Open Graph metadata", "LOW"
    )

    result = agent.generate([discoverability_issue, comprehension_issue, _csp_issue()])
    _print_recommendation("merged open_graph", result.recommendations[0])

    # Merged into one open_graph recommendation + the separate csp one = 2, not 3.
    assert len(result.recommendations) == 2

    merged = next(rec for rec in result.recommendations if rec.criterion == "open_graph")
    # Highest priority among the merged group wins.
    assert merged.priority == "MEDIUM"
    # Both categories are visible, not silently dropped.
    assert "discoverability" in merged.category
    assert "comprehension" in merged.category
    # A single, clean sentence — not "message A / message B".
    assert merged.issue == "No Open Graph metadata found"
    # Retriever was only called once for the merged group, not once per duplicate.
    assert sum(1 for call in retriever.calls if call["criterion"] == "open_graph") == 1


def test_criteria_in_the_same_merge_group_are_merged_too() -> None:
    """api_discoverability and api_documentation both boil down to "publish API docs"."""
    retriever = _FakeRetriever(documents=[])
    agent = RecommendationAgent(
        retriever=retriever,
        prompt_builder=PromptBuilder(),
        llm_client=TemplateLLMClient(),
    )

    api_discoverability_issue = ClassifiedIssue(
        category="discoverability",
        issue="No API documentation found",
        priority="MEDIUM",
        knowledge_topic="api_discoverability",
        reason="No discoverable API surface prevents agents from finding a programmatic entry point.",
        criterion="api_discoverability",
        score=42.0,
        evidence={"api_discoverability": False},
        retrieval_query={"category": "discoverability", "criterion": "api_discoverability"},
    )
    api_documentation_issue = ClassifiedIssue(
        category="interaction",
        issue="No API documentation available.",
        priority="MEDIUM",
        knowledge_topic="openapi",
        reason="Missing API documentation prevents agents from learning how to call the API.",
        criterion="api_documentation",
        score=0.0,
        evidence={"api_documentation": False},
        retrieval_query={"category": "interaction", "criterion": "api_documentation"},
    )

    result = agent.generate([api_discoverability_issue, api_documentation_issue])

    # Both collapse into a single "publish API docs" recommendation.
    assert len(result.recommendations) == 1
    merged = result.recommendations[0]
    assert merged.criterion in ("api_discoverability", "api_documentation")
    assert "discoverability" in merged.category
    assert "interaction" in merged.category
    assert merged.issue in ("No API documentation found", "No API documentation available.")


def test_unrelated_criteria_are_never_merged() -> None:
    """A sanity check that merging is scoped — csp and sitemap stay separate."""
    retriever = _FakeRetriever(documents=[])
    agent = RecommendationAgent(
        retriever=retriever,
        prompt_builder=PromptBuilder(),
        llm_client=TemplateLLMClient(),
    )

    sitemap_issue = ClassifiedIssue(
        category="discoverability",
        issue="No sitemap.xml found",
        priority="MEDIUM",
        knowledge_topic="sitemap",
        reason="Missing sitemap.xml slows down content discovery for crawlers and agents.",
        criterion="sitemap",
        score=57.14,
        evidence={"sitemap": False},
        retrieval_query={"category": "discoverability", "criterion": "sitemap"},
    )

    result = agent.generate([_csp_issue(), sitemap_issue])

    assert len(result.recommendations) == 2
    criteria = {rec.criterion for rec in result.recommendations}
    assert criteria == {"csp", "sitemap"}


if __name__ == "__main__":
    test_csp_issue_produces_a_full_recommendation()
    test_no_retrieved_documents_is_handled_gracefully()
    test_uninitialized_retriever_is_handled_gracefully()
    test_mocked_llm_response_is_parsed_into_recommendation_fields()
    test_llm_failure_falls_back_to_a_structured_recommendation()
    test_llm_failure_with_no_documents_still_returns_a_recommendation()
    test_summary_counts_recommendations_per_priority()
    test_same_criterion_issues_are_merged_into_one_recommendation()
    test_criteria_in_the_same_merge_group_are_merged_too()
    test_unrelated_criteria_are_never_merged()
    print("All tests passed.")

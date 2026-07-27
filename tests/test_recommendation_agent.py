"""Tests for :class:`RecommendationAgent` and the Groq LLM integration.

Uses real ARAS flow data: the exact mytek.tn-derived issue set from
`tests/test_rule_engine.py`, classified by the real `RuleEngine`, fed
into `RecommendationAgent` backed by a real, freshly-ingested ChromaDB
vector store (via `KnowledgeIngestion` + `VectorStoreManager`) and the
real `KnowledgeRetriever`.

Two tests exercise the real production path end-to-end, including a
genuine call to Groq via `GroqLLMClient` (`RecommendationAgent`'s
default) — these require network access and a valid `GROQ_API_KEY`
(loaded from `.env`). All other tests inject `TemplateLLMClient` (a
deterministic, offline test double) or a recording mock, exactly as
suggested for environments without API access, so the rest of the
suite never depends on network availability or Groq's non-deterministic
phrasing.
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape as _xml_escape

# Allow running this file directly (e.g. from an IDE "Run" button) by
# ensuring the project root is importable, not just the `tests/` folder.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from agents.rule_engine import RuleEngine
from models.recommendation import Recommendation, RecommendationResult
from models.rule_engine import ClassifiedIssue
from orchestrator.agent import ARASOrchestrator
from recommendation.agent import RecommendationAgent
from recommendation.llm_client import GroqLLMClient, LLMClient, TemplateLLMClient
from recommendation.rag.ingestion import KnowledgeIngestion
from recommendation.rag.retriever import KnowledgeRetriever
from recommendation.rag.vector_store import VectorStoreManager

KNOWLEDGE_PATH = str(Path(__file__).resolve().parent.parent / "recommendation" / "knowledge")
GROQ_API_KEY_ENV_VAR = "GROQ_API_KEY"


class _FakeFailingLLMClient(LLMClient):
    """Always-failing `LLMClient`, used to exercise the fallback path."""

    def generate(self, prompt: str) -> str:
        raise RuntimeError("simulated LLM outage")


class _RecordingMockLLMClient(LLMClient):
    """Mock `LLMClient` that records every prompt it was called with.

    Used to verify `RecommendationAgent`'s wiring (it calls
    `llm_client.generate(prompt)` once per issue and uses the returned
    text) without depending on `GroqLLMClient` or real network access,
    per the task's request for "a mock LLMClient test without changing
    the production implementation."
    """

    def __init__(self, response: str) -> None:
        self.response = response
        self.calls: list[str] = []

    def generate(self, prompt: str) -> str:
        self.calls.append(prompt)
        return self.response


def _build_test_retriever() -> tuple[KnowledgeRetriever, Path]:
    """Ingest the real knowledge base into a fresh, isolated vector store.

    Returns:
        A tuple of `(initialized retriever, persist directory)`. The
        caller is responsible for removing the persist directory once done.
    """
    persist_directory = Path(tempfile.mkdtemp(prefix="aras_recommendation_test_"))
    chunks = KnowledgeIngestion().ingest(KNOWLEDGE_PATH)
    VectorStoreManager(persist_directory=persist_directory).create_vector_store(chunks)

    retriever = KnowledgeRetriever()
    retriever.initialize(str(persist_directory))
    return retriever, persist_directory


def _mytek_classified_issues() -> list[ClassifiedIssue]:
    """Classify the real mytek.tn-derived issue set via the real Rule Engine."""
    from dataclasses import dataclass, field

    @dataclass
    class _FakeAnalysisResult:
        issues: list[str] = field(default_factory=list)

    analysis_results = {
        "security": _FakeAnalysisResult(issues=["Missing Content-Security-Policy header."]),
        "comprehension": _FakeAnalysisResult(issues=["No JSON-LD semantic information found"]),
    }
    return RuleEngine().evaluate(analysis_results).issues


def _print_debug_output(classified_issue: ClassifiedIssue, recommendation: Recommendation) -> None:
    print(f"Issue:\n{classified_issue.issue}\n")
    print(f"Retrieved knowledge:\n{', '.join(recommendation.references) or '(none)'}\n")
    print(f"Generated recommendation:\n{recommendation.recommendation}\n")
    print(f"Explanation:\n{recommendation.explanation}\n")
    print(f"Implementation steps:\n{recommendation.implementation_steps}\n")
    print("-" * 40)


# ---------------------------------------------------------------------------
# End-to-end tests using the real production default (GroqLLMClient).
# Require network access and a valid GROQ_API_KEY (loaded from .env).
# ---------------------------------------------------------------------------


def test_generate_produces_two_grounded_recommendations_via_groq() -> None:
    """Full production path: RuleEngine -> Retriever/ChromaDB -> GroqLLMClient.

    Verifies retrieval, prompt generation, a real Groq call, and that
    the final `RecommendationResult` shape is unchanged by the LLM
    backend migration.
    """
    retriever, persist_directory = _build_test_retriever()

    try:
        classified_issues = _mytek_classified_issues()
        assert len(classified_issues) == 2

        # No llm_client passed: exercises RecommendationAgent's real
        # default, GroqLLMClient, confirming it successfully calls Groq.
        agent = RecommendationAgent(retriever=retriever)
        result = agent.generate(classified_issues)

        for classified_issue, recommendation in zip(classified_issues, result.recommendations):
            _print_debug_output(classified_issue, recommendation)

        assert isinstance(result, RecommendationResult)
        assert len(result.recommendations) == 2

        by_category = {rec.category: rec for rec in result.recommendations}

        # Category and priority are preserved unchanged from the Rule Engine
        # — the LLM backend migration does not affect this.
        assert by_category["security"].category == "security"
        assert by_category["security"].priority == "HIGH"
        assert by_category["security"].issue == "Missing Content-Security-Policy header."

        assert by_category["comprehension"].category == "comprehension"
        assert by_category["comprehension"].priority == "MEDIUM"
        assert by_category["comprehension"].issue == "No JSON-LD semantic information found"

        # Retrieved knowledge was actually used: references point at the
        # correct knowledge-base source files (Retriever/ChromaDB unaffected).
        assert "knowledge/security/csp.md" in by_category["security"].references
        assert "knowledge/comprehension/jsonld.md" in by_category["comprehension"].references

        # RecommendationResult format is unchanged: every field populated.
        for recommendation in result.recommendations:
            assert recommendation.explanation.strip()
            assert recommendation.recommendation.strip()
            assert len(recommendation.implementation_steps) > 0

        assert result.summary == {"HIGH": 1, "MEDIUM": 1, "LOW": 0}
    finally:
        shutil.rmtree(persist_directory, ignore_errors=True)


def test_generate_without_retriever_still_produces_recommendations_via_groq() -> None:
    """Case 1 against the real Groq backend: no retrieved documents."""
    classified_issue = ClassifiedIssue(
        category="security",
        issue="Missing Content-Security-Policy header.",
        priority="HIGH",
        knowledge_topic="csp",
        reason="Missing CSP leaves the site open to script injection and XSS attacks.",
    )

    # An uninitialized retriever: RecommendationAgent must not crash or
    # attempt a real retrieval call, and still calls the real Groq default.
    agent = RecommendationAgent(retriever=KnowledgeRetriever())
    result = agent.generate([classified_issue])

    assert len(result.recommendations) == 1
    recommendation = result.recommendations[0]
    print(f"No-retrieval recommendation (Groq): {recommendation}")

    assert recommendation.category == "security"
    assert recommendation.priority == "HIGH"
    assert recommendation.references == []
    assert recommendation.explanation.strip()
    assert recommendation.recommendation.strip()
    assert len(recommendation.implementation_steps) > 0


# ---------------------------------------------------------------------------
# Offline tests: TemplateLLMClient / mocks / fakes only, no network required.
# ---------------------------------------------------------------------------


def test_generate_falls_back_when_llm_fails() -> None:
    """Case 2: LLM failure -> a structured fallback recommendation is returned."""
    retriever, persist_directory = _build_test_retriever()

    try:
        classified_issue = ClassifiedIssue(
            category="security",
            issue="Missing Content-Security-Policy header.",
            priority="HIGH",
            knowledge_topic="csp",
            reason="Missing CSP leaves the site open to script injection and XSS attacks.",
        )

        agent = RecommendationAgent(retriever=retriever, llm_client=_FakeFailingLLMClient())
        result = agent.generate([classified_issue])

        assert len(result.recommendations) == 1
        recommendation = result.recommendations[0]
        print(f"Fallback recommendation: {recommendation}")

        # The fallback is still a fully-formed, non-empty recommendation.
        assert recommendation.category == "security"
        assert recommendation.priority == "HIGH"
        assert recommendation.explanation.strip()
        assert recommendation.recommendation.strip()
        assert len(recommendation.implementation_steps) > 0
        assert "knowledge/security/csp.md" in recommendation.references
    finally:
        shutil.rmtree(persist_directory, ignore_errors=True)


def test_summary_counts_priorities_across_all_recommendations() -> None:
    """The summary dict always reports all three priority levels."""
    classified_issues = [
        ClassifiedIssue("security", "issue A", "HIGH", "csp", "reason A"),
        ClassifiedIssue("interaction", "issue B", "MEDIUM", "openapi", "reason B"),
        ClassifiedIssue("discoverability", "issue C", "LOW", "llms", "reason C"),
    ]

    agent = RecommendationAgent(
        retriever=KnowledgeRetriever(), llm_client=TemplateLLMClient()
    )
    result = agent.generate(classified_issues)

    assert result.summary == {"HIGH": 1, "MEDIUM": 1, "LOW": 1}


def test_empty_input_produces_empty_result() -> None:
    """No classified issues -> no recommendations, zeroed summary."""
    agent = RecommendationAgent(
        retriever=KnowledgeRetriever(), llm_client=TemplateLLMClient()
    )
    result = agent.generate([])

    assert result.recommendations == []
    assert result.summary == {"HIGH": 0, "MEDIUM": 0, "LOW": 0}


def test_recommendation_agent_calls_configured_llm_client_per_issue() -> None:
    """Mock LLMClient test: verifies the agent's wiring without touching Groq.

    Confirms `RecommendationAgent` calls `llm_client.generate(prompt)`
    exactly once per classified issue, and that each returned recommendation
    is built from that mock's response — independent of whether the real
    `GroqLLMClient` (production) or any other backend is configured.
    """
    mock_llm_client = _RecordingMockLLMClient(
        response=(
            "EXPLANATION:\nMocked explanation.\n\n"
            "RECOMMENDATION:\nMocked recommendation.\n\n"
            "IMPLEMENTATION STEPS:\n- Mocked step one.\n- Mocked step two.\n"
        )
    )
    classified_issues = [
        ClassifiedIssue("security", "issue A", "HIGH", "csp", "reason A"),
        ClassifiedIssue("comprehension", "issue B", "MEDIUM", "jsonld", "reason B"),
    ]

    agent = RecommendationAgent(retriever=KnowledgeRetriever(), llm_client=mock_llm_client)
    result = agent.generate(classified_issues)

    assert len(mock_llm_client.calls) == 2
    assert "issue A" in mock_llm_client.calls[0]
    assert "issue B" in mock_llm_client.calls[1]

    for recommendation in result.recommendations:
        assert recommendation.explanation == "Mocked explanation."
        assert recommendation.recommendation == "Mocked recommendation."
        assert recommendation.implementation_steps == ["Mocked step one.", "Mocked step two."]


# ---------------------------------------------------------------------------
# GroqLLMClient-specific tests.
# ---------------------------------------------------------------------------


def test_groq_llm_client_raises_when_api_key_missing() -> None:
    """Missing GROQ_API_KEY must fail clearly and immediately."""
    original_value = os.environ.pop(GROQ_API_KEY_ENV_VAR, None)
    try:
        try:
            GroqLLMClient()
            assert False, "expected ValueError for missing GROQ_API_KEY"
        except ValueError as error:
            print(f"expected error: {error}")
            assert GROQ_API_KEY_ENV_VAR in str(error)
    finally:
        if original_value is not None:
            os.environ[GROQ_API_KEY_ENV_VAR] = original_value


def test_groq_llm_client_generates_real_response() -> None:
    """`GroqLLMClient.generate` successfully calls Groq and returns text.

    Requires network access and a valid GROQ_API_KEY.
    """
    client = GroqLLMClient()
    prompt = (
        "Website issue: Missing Content Security Policy\n"
        "Category: security\n"
        "Priority: HIGH\n"
        "Technical knowledge:\nCSP mitigates XSS attacks.\n\n"
        "Instruction:\nRespond with EXPLANATION:, RECOMMENDATION:, and "
        "IMPLEMENTATION STEPS: sections."
    )

    response = client.generate(prompt)
    print(f"Groq response:\n{response}")

    assert isinstance(response, str)
    assert response.strip()


# ---------------------------------------------------------------------------
# End-to-end scenario: real website -> ARASOrchestrator (Evidence Collector +
# all four analysis agents) -> Rule Engine -> Recommendation Agent (real
# ChromaDB retrieval + real Groq generation) -> PDF report.
#
# This section adds no logic to any agent; it only orchestrates the existing
# components and renders their output, mirroring the real-site scenarios
# already used for the Discoverability/Comprehension/Interaction/Security/
# Scoring agents and the orchestrator itself.
# ---------------------------------------------------------------------------

TARGET_URL = "https://www.mytek.tn"
REPORT_PATH = Path(__file__).resolve().parent.parent / "recommendation_report_mytek.pdf"

_PRIORITY_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}


def _escape(text: str) -> str:
    """Escape text so ReportLab's mini-XML paragraph parser treats it as plain text.

    Real Groq-generated text can contain raw angle brackets or
    ampersands (e.g. a literal `<meta ...>` snippet quoted as an
    example), which `reportlab.platypus.Paragraph` would otherwise try
    to parse as markup and reject. Only the literal `<b>...</b>` tags
    this module writes itself are left unescaped.

    Args:
        text: Untrusted, dynamically generated text (LLM output).

    Returns:
        `text` with `&`, `<`, and `>` escaped to their XML entities.
    """
    return _xml_escape(text)


def _generate_pdf_report(url: str, result: RecommendationResult, output_path: Path) -> None:
    """Render a `RecommendationResult` as a professional PDF report.

    Args:
        url: The website URL that was assessed.
        result: The output of `RecommendationAgent.generate`.
        output_path: Filesystem path the PDF should be written to.
    """
    styles = getSampleStyleSheet()
    heading_style = ParagraphStyle(
        "SectionHeading", parent=styles["Heading2"], spaceBefore=12, spaceAfter=6
    )
    sub_heading_style = ParagraphStyle(
        "SubHeading", parent=styles["Heading3"], spaceBefore=10, spaceAfter=4
    )

    ordered_recommendations = sorted(
        result.recommendations, key=lambda rec: _PRIORITY_ORDER.get(rec.priority, 3)
    )

    story: list[Any] = [
        Paragraph("ARAS Recommendation Report", styles["Title"]),
        Spacer(1, 0.5 * cm),
        Paragraph(f"<b>Website:</b> {_escape(url)}", styles["Normal"]),
        Paragraph(
            f"<b>Analysis date:</b> {datetime.now(timezone.utc).isoformat()}",
            styles["Normal"],
        ),
        Paragraph("<b>Agent used:</b> Recommendation Agent (RAG + Groq/Llama 3.1)", styles["Normal"]),
    ]

    # Section 1: Executive summary
    story.append(Paragraph("1. Executive Summary", heading_style))
    story.append(
        Paragraph(f"<b>Total recommendations:</b> {len(result.recommendations)}", styles["Normal"])
    )
    story.append(Paragraph(f"<b>HIGH priority:</b> {result.summary.get('HIGH', 0)}", styles["Normal"]))
    story.append(Paragraph(f"<b>MEDIUM priority:</b> {result.summary.get('MEDIUM', 0)}", styles["Normal"]))
    story.append(Paragraph(f"<b>LOW priority:</b> {result.summary.get('LOW', 0)}", styles["Normal"]))

    # Section 2: Summary table
    story.append(Paragraph("2. Recommendations Overview", heading_style))
    table_data = [["Priority", "Category", "Issue"]]
    for recommendation in ordered_recommendations:
        table_data.append(
            [
                recommendation.priority,
                recommendation.category,
                _escape(recommendation.issue),
            ]
        )

    overview_table = Table(table_data, colWidths=[2.5 * cm, 3.5 * cm, 10 * cm])
    overview_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E3440")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(overview_table)

    # Section 3: Detailed recommendations, one subsection per issue.
    story.append(Paragraph("3. Detailed Recommendations", heading_style))
    for index, recommendation in enumerate(ordered_recommendations, start=1):
        story.append(
            Paragraph(
                f"{index}. [{recommendation.priority}] {_escape(recommendation.category)} — "
                f"{_escape(recommendation.issue)}",
                sub_heading_style,
            )
        )
        story.append(
            Paragraph(f"<b>Explanation:</b> {_escape(recommendation.explanation)}", styles["Normal"])
        )
        story.append(
            Paragraph(
                f"<b>Recommendation:</b> {_escape(recommendation.recommendation)}", styles["Normal"]
            )
        )
        if recommendation.implementation_steps:
            story.append(Paragraph("<b>Implementation steps:</b>", styles["Normal"]))
            story.append(
                ListFlowable(
                    [
                        ListItem(Paragraph(_escape(step), styles["Normal"]))
                        for step in recommendation.implementation_steps
                    ],
                    bulletType="bullet",
                )
            )
        references = (
            ", ".join(recommendation.references) if recommendation.references else "none"
        )
        story.append(Paragraph(f"<b>References:</b> {_escape(references)}", styles["Normal"]))

    SimpleDocTemplate(str(output_path), pagesize=A4).build(story)


def _print_console_summary(url: str, result: RecommendationResult, report_path: Path) -> None:
    """Print the human-facing summary of a real-site recommendation run.

    Args:
        url: The website URL that was assessed.
        result: The output of `RecommendationAgent.generate`.
        report_path: Filesystem path the PDF report was written to.
    """
    print("=" * 40)
    print("ARAS Recommendation Report")
    print(f"Website: {url}")
    print()
    print(f"Total recommendations: {len(result.recommendations)}")
    print(f"Summary: {result.summary}")
    print()
    for recommendation in sorted(
        result.recommendations, key=lambda rec: _PRIORITY_ORDER.get(rec.priority, 3)
    ):
        print(f"[{recommendation.priority}] {recommendation.category}: {recommendation.issue}")
        print(f"  -> {recommendation.recommendation}")
    print()
    print("PDF generated:")
    print(report_path)
    print("=" * 40)


def test_mytek_real_site_recommendation_report() -> None:
    """End-to-end: collect real issues from mytek.tn, generate recommendations, render a PDF.

    Runs the full ARAS pipeline against a live website:
    `ARASOrchestrator` (Evidence Collector + Discoverability/
    Comprehension/Interaction/Security agents) -> `RuleEngine` -> real
    `KnowledgeRetriever`/ChromaDB -> real `GroqLLMClient`. Requires
    network access and a valid GROQ_API_KEY.
    """
    orchestrator_state = ARASOrchestrator().run(TARGET_URL)

    rule_engine_result = RuleEngine().evaluate(
        {
            "discoverability": orchestrator_state["discoverability_result"],
            "comprehension": orchestrator_state["comprehension_result"],
            "interaction": orchestrator_state["interaction_result"],
            "security": orchestrator_state["security_result"],
        }
    )
    print(f"Classified issues: {len(rule_engine_result.issues)}")
    assert len(rule_engine_result.issues) > 0

    retriever, persist_directory = _build_test_retriever()
    try:
        agent = RecommendationAgent(retriever=retriever)
        result = agent.generate(rule_engine_result.issues)

        _generate_pdf_report(TARGET_URL, result, REPORT_PATH)
        _print_console_summary(TARGET_URL, result, REPORT_PATH)

        assert REPORT_PATH.exists()
        assert len(result.recommendations) == len(rule_engine_result.issues)
        assert sum(result.summary.values()) == len(result.recommendations)
        for recommendation in result.recommendations:
            assert recommendation.explanation.strip()
            assert recommendation.recommendation.strip()
            assert len(recommendation.implementation_steps) > 0
    finally:
        shutil.rmtree(persist_directory, ignore_errors=True)


if __name__ == "__main__":
    test_generate_produces_two_grounded_recommendations_via_groq()
    test_generate_without_retriever_still_produces_recommendations_via_groq()
    test_generate_falls_back_when_llm_fails()
    test_summary_counts_priorities_across_all_recommendations()
    test_empty_input_produces_empty_result()
    test_recommendation_agent_calls_configured_llm_client_per_issue()
    test_groq_llm_client_raises_when_api_key_missing()
    test_groq_llm_client_generates_real_response()
    test_mytek_real_site_recommendation_report()
    print("All tests passed.")

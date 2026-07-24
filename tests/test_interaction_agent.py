"""Unit tests for :class:`InteractionAgent`.

Covers a fully agent-ready website, a REST-API-only website, an
MCP-only website, a frontend-only website, and a website with no
interaction surfaces at all. The agent consumes only a
`WebsiteEvidence` instance built by hand here — no network access,
HTML parsing, or API/frontend discovery tool is exercised by these
tests.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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

from agents.evidence_collector import EvidenceCollectorAgent
from agents.interaction_agent import InteractionAgent
from models.evidence import WebsiteEvidence
from models.interaction import InteractionResult

URL = "https://www.example.com"


def _print_result(label: str, result) -> None:
    print(f"--- {label} ---")
    print(f"score:           {result.score}")
    print(f"checks:          {result.checks}")
    print(f"details:         {result.details}")
    print(f"issues:          {result.issues}")
    print(f"recommendations: {result.recommendations}")
    print()


def _fully_agent_ready_evidence() -> WebsiteEvidence:
    """Build a `WebsiteEvidence` that should pass every criterion."""
    return WebsiteEvidence(
        url=URL,
        status_code=200,
        api_analysis={
            "api_endpoints": ["https://www.example.com/api/products"],
            "openapi_urls": ["https://www.example.com/openapi.json"],
            "swagger_urls": [],
            "redoc_urls": [],
            "api_documentation_urls": [],
            "graphql_endpoints": ["https://www.example.com/graphql"],
            "mcp_endpoints": ["https://www.example.com/mcp"],
            "mcp_resources": [],
            "mcp_tools": ["search", "add_to_cart"],
        },
        frontend_analysis={
            "discovered_api_urls": ["/api/search"],
            "graphql_references": [],
            "websocket_references": [],
        },
    )


def test_fully_agent_ready_website_scores_100() -> None:
    """Every criterion passes: the score should be exactly 100."""
    agent = InteractionAgent()

    result = agent.evaluate(_fully_agent_ready_evidence())
    _print_result("fully agent-ready website", result)

    assert result.score == 100.0
    assert all(result.checks.values())
    assert result.issues == []
    assert result.recommendations == []


def test_only_rest_api_scores_partially() -> None:
    """Only a backend API exists: partial score, other criteria fail."""
    agent = InteractionAgent()
    evidence = WebsiteEvidence(
        url=URL,
        api_analysis={"api_endpoints": ["https://www.example.com/api/products"]},
    )

    result = agent.evaluate(evidence)
    _print_result("only REST API", result)

    assert result.checks["api_availability"] is True
    assert result.checks["api_documentation"] is False
    assert result.checks["graphql"] is False
    assert result.checks["mcp_endpoint"] is False
    assert result.checks["mcp_tools"] is False
    assert result.checks["frontend_interaction"] is False
    assert 0.0 < result.score < 100.0


def test_only_mcp_tools_pass() -> None:
    """Only MCP tools exist: the MCP-tools criterion passes in isolation."""
    agent = InteractionAgent()
    evidence = WebsiteEvidence(
        url=URL,
        api_analysis={"mcp_tools": ["search"]},
    )

    result = agent.evaluate(evidence)
    _print_result("only MCP tools", result)

    assert result.checks["mcp_tools"] is True
    assert result.checks["mcp_endpoint"] is False
    assert result.checks["api_availability"] is False
    assert "No MCP tools or resources available." not in result.issues


def test_documentation_only_does_not_count_as_api_availability() -> None:
    """OpenAPI docs alone are not an executable surface: availability stays False.

    Regression test for the bug where a documentation-only website
    (spec published, but no proven callable endpoint) was expected to
    satisfy `api_availability` just because `openapi_urls` was
    populated. Documentation is its own, separately-scored criterion.
    """
    agent = InteractionAgent()
    evidence = WebsiteEvidence(
        url=URL,
        api_analysis={
            "openapi_urls": ["https://www.example.com/openapi.json"],
            "api_endpoints": [],
            "graphql_endpoints": [],
        },
    )

    result = agent.evaluate(evidence)
    _print_result("documentation only", result)

    assert result.checks["api_availability"] is False
    assert result.checks["api_documentation"] is True
    assert "No executable API interaction surface detected." in result.issues


def test_graphql_only_counts_as_api_availability() -> None:
    """A GraphQL endpoint alone is an executable surface: availability passes too.

    Regression test for the bug where `_evaluate_api_availability` only
    inspected `api_endpoints`, so a GraphQL-only website was
    underestimated even though GraphQL is just as executable as REST.
    """
    agent = InteractionAgent()
    evidence = WebsiteEvidence(
        url=URL,
        api_analysis={"graphql_endpoints": ["https://www.example.com/graphql"]},
    )

    result = agent.evaluate(evidence)
    _print_result("GraphQL only", result)

    assert result.checks["api_availability"] is True
    assert result.checks["graphql"] is True
    assert result.checks["api_documentation"] is False


def test_no_interaction_surfaces_scores_near_zero() -> None:
    """A bare, empty evidence record should score at (or near) zero."""
    agent = InteractionAgent()
    evidence = WebsiteEvidence(url=URL)

    result = agent.evaluate(evidence)
    _print_result("no interaction surfaces", result)

    assert result.score == 0.0
    assert all(passed is False for passed in result.checks.values())
    assert len(result.issues) == 6
    assert len(result.recommendations) == 6


def test_frontend_only_interactions_pass() -> None:
    """Only frontend-discovered interactions exist: that criterion passes."""
    agent = InteractionAgent()
    evidence = WebsiteEvidence(
        url=URL,
        frontend_analysis={
            "discovered_api_urls": [],
            "graphql_references": ["/graphql"],
            "websocket_references": ["wss://www.example.com/live"],
        },
    )

    result = agent.evaluate(evidence)
    _print_result("frontend-only interactions", result)

    assert result.checks["frontend_interaction"] is True
    assert result.checks["api_availability"] is False
    assert result.checks["graphql"] is False
    assert "No actionable frontend interaction detected." not in result.issues


# ---------------------------------------------------------------------------
# End-to-end scenario: real website -> Evidence Collector -> Interaction
# Agent -> PDF report.
#
# This section adds no logic to either agent; it only orchestrates the two
# existing components and renders their output. Mirrors the equivalent
# scenario in test_discoverability_agent.py / test_comprehension_agent.py.
# ---------------------------------------------------------------------------

TARGET_URL = "https://www.mytek.tn"
REPORT_PATH = Path(__file__).resolve().parent.parent / "interaction_report_mytek.pdf"

# Maps each `InteractionResult.checks` key to its human-readable label,
# used when rendering the criteria table in the PDF report.
_CRITERIA_LABELS: dict[str, str] = {
    "api_availability": "Backend API availability",
    "api_documentation": "API documentation availability",
    "graphql": "GraphQL availability",
    "mcp_endpoint": "MCP endpoint availability",
    "mcp_tools": "MCP tools and resources",
    "frontend_interaction": "Frontend interaction capabilities",
}


def _criterion_detail_summary(name: str, details: dict[str, Any]) -> str:
    """Summarize the supporting evidence for a single criterion.

    Args:
        name: The criterion's key in `InteractionResult.checks`.
        details: The full `InteractionResult.details` mapping.

    Returns:
        A short, human-readable description of the evidence backing
        this criterion's pass/fail outcome.
    """
    if name == "api_availability":
        return f"endpoints={len(details.get('api_endpoints') or [])}"
    if name == "api_documentation":
        total = (
            len(details.get("openapi_urls") or [])
            + len(details.get("swagger_urls") or [])
            + len(details.get("redoc_urls") or [])
            + len(details.get("api_documentation_urls") or [])
        )
        return f"docs found={total}"
    if name == "graphql":
        return f"endpoints={details.get('graphql_endpoints') or []}"
    if name == "mcp_endpoint":
        return f"endpoints={details.get('mcp_endpoints') or []}"
    if name == "mcp_tools":
        return (
            f"tools={details.get('mcp_tools') or []}, "
            f"resources={details.get('mcp_resources') or []}"
        )
    if name == "frontend_interaction":
        return f"actions={details.get('frontend_actions') or []}"
    return ""


def _generate_pdf_report(
    url: str, result: InteractionResult, output_path: Path
) -> None:
    """Render an `InteractionResult` as a PDF report.

    Args:
        url: The website URL that was assessed.
        result: The evaluation produced by `InteractionAgent.evaluate`.
        output_path: Filesystem path the PDF should be written to.
    """
    styles = getSampleStyleSheet()
    heading_style = ParagraphStyle(
        "SectionHeading", parent=styles["Heading2"], spaceBefore=12, spaceAfter=6
    )

    passed_count = sum(1 for outcome in result.checks.values() if outcome)
    failed_count = len(result.checks) - passed_count

    story: list[Any] = [
        Paragraph("ARAS Interaction Assessment Report", styles["Title"]),
        Spacer(1, 0.5 * cm),
        Paragraph(f"<b>Website URL:</b> {url}", styles["Normal"]),
        Paragraph(
            f"<b>Analysis date:</b> {datetime.now(timezone.utc).isoformat()}",
            styles["Normal"],
        ),
        Paragraph("<b>Agent used:</b> Interaction Agent", styles["Normal"]),
    ]

    # Section 1: Overall score
    story.append(Paragraph("1. Overall Score", heading_style))
    story.append(Paragraph(f"<b>Score:</b> {result.score}/100", styles["Normal"]))
    story.append(Paragraph(f"<b>Criteria passed:</b> {passed_count}", styles["Normal"]))
    story.append(Paragraph(f"<b>Criteria failed:</b> {failed_count}", styles["Normal"]))

    # Section 2: Criteria evaluation table
    story.append(Paragraph("2. Criteria Evaluation", heading_style))
    table_data = [["Criterion", "Status", "Details"]]
    for name, label in _CRITERIA_LABELS.items():
        status = "PASS" if result.checks.get(name) else "FAIL"
        table_data.append([label, status, _criterion_detail_summary(name, result.details)])

    criteria_table = Table(table_data, colWidths=[5 * cm, 2.5 * cm, 8.5 * cm])
    criteria_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E3440")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
            ]
        )
    )
    story.append(criteria_table)

    # Section 3: Evidence details
    story.append(Paragraph("3. Evidence Details", heading_style))
    details = result.details
    evidence_lines = [
        f"API endpoints: {details.get('api_endpoints') or []}",
        f"OpenAPI URLs: {details.get('openapi_urls') or []}",
        f"Swagger URLs: {details.get('swagger_urls') or []}",
        f"ReDoc URLs: {details.get('redoc_urls') or []}",
        f"API documentation URLs: {details.get('api_documentation_urls') or []}",
        f"GraphQL endpoints: {details.get('graphql_endpoints') or []}",
        f"MCP endpoints: {details.get('mcp_endpoints') or []}",
        f"MCP tools: {details.get('mcp_tools') or []}",
        f"MCP resources: {details.get('mcp_resources') or []}",
        f"Frontend actions: {details.get('frontend_actions') or []}",
    ]
    story.append(
        ListFlowable(
            [ListItem(Paragraph(line, styles["Normal"])) for line in evidence_lines],
            bulletType="bullet",
        )
    )

    # Section 4: Issues
    story.append(Paragraph("4. Issues", heading_style))
    if result.issues:
        story.append(
            ListFlowable(
                [ListItem(Paragraph(issue, styles["Normal"])) for issue in result.issues],
                bulletType="bullet",
            )
        )
    else:
        story.append(Paragraph("No issues found.", styles["Normal"]))

    # Section 5: Recommendations
    story.append(Paragraph("5. Recommendations", heading_style))
    if result.recommendations:
        story.append(
            ListFlowable(
                [
                    ListItem(Paragraph(recommendation, styles["Normal"]))
                    for recommendation in result.recommendations
                ],
                bulletType="bullet",
            )
        )
    else:
        story.append(Paragraph("No recommendations.", styles["Normal"]))

    SimpleDocTemplate(str(output_path), pagesize=A4).build(story)


def _print_console_summary(url: str, result: InteractionResult, report_path: Path) -> None:
    """Print the human-facing summary of a real-site assessment run.

    Args:
        url: The website URL that was assessed.
        result: The evaluation produced by `InteractionAgent.evaluate`.
        report_path: Filesystem path the PDF report was written to.
    """
    # Windows consoles often default to a legacy code page (cp1252) that
    # cannot encode ✓/✗; fall back to ASCII markers rather than crash.
    try:
        "✓".encode(sys.stdout.encoding or "utf-8")
        pass_mark, fail_mark = "✓", "✗"
    except UnicodeEncodeError:
        pass_mark, fail_mark = "[PASS]", "[FAIL]"

    print("=" * 30)
    print("ARAS Interaction Report")
    print(f"Website: {url}")
    print()
    print(f"Score: {result.score}/100")
    print()
    print("Checks:")
    for name, label in _CRITERIA_LABELS.items():
        mark = pass_mark if result.checks.get(name) else fail_mark
        print(f"{mark} {label}")
    print()
    print("PDF generated:")
    print(report_path)
    print("=" * 30)


def test_mytek_real_site_interaction_report() -> None:
    """End-to-end: collect real evidence, evaluate it, render a PDF report.

    Chains the existing `EvidenceCollectorAgent` into the existing
    `InteractionAgent` against a live website, then renders the
    resulting `InteractionResult` as a PDF. Requires network access.
    """
    evidence = EvidenceCollectorAgent().collect(TARGET_URL)
    result = InteractionAgent().evaluate(evidence)
    _print_result(f"real site: {TARGET_URL}", result)

    _generate_pdf_report(TARGET_URL, result, REPORT_PATH)
    _print_console_summary(TARGET_URL, result, REPORT_PATH)

    assert REPORT_PATH.exists()
    assert 0.0 <= result.score <= 100.0
    assert len(result.checks) == 6


if __name__ == "__main__":
    test_fully_agent_ready_website_scores_100()
    test_only_rest_api_scores_partially()
    test_only_mcp_tools_pass()
    test_documentation_only_does_not_count_as_api_availability()
    test_graphql_only_counts_as_api_availability()
    test_no_interaction_surfaces_scores_near_zero()
    test_frontend_only_interactions_pass()
    test_mytek_real_site_interaction_report()
    print("All tests passed.")

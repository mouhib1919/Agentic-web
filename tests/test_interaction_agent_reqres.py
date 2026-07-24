"""End-to-end test of :class:`InteractionAgent` against a second real website.

`https://www.mytek.tn` (used in `test_interaction_agent.py`) scores 0/100
because it is a plain e-commerce storefront with no discoverable API
surface. This module chains the existing `EvidenceCollectorAgent` into the
existing `InteractionAgent` against `https://reqres.in` — a public REST API
demo site — to exercise the agent against a website that actually exposes
machine-readable interaction surfaces, and renders the resulting
`InteractionResult` as a PDF report.

This adds no logic to either agent; it only orchestrates the two existing
components and renders their output, mirroring the mytek.tn scenario in
`test_interaction_agent.py`.

Requires network access.
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
from models.interaction import InteractionResult

TARGET_URL = "https://reqres.in"
REPORT_PATH = Path(__file__).resolve().parent.parent / "interaction_report_reqres.pdf"

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


def _print_result(label: str, result: InteractionResult) -> None:
    print(f"--- {label} ---")
    print(f"score:           {result.score}")
    print(f"checks:          {result.checks}")
    print(f"details:         {result.details}")
    print(f"issues:          {result.issues}")
    print(f"recommendations: {result.recommendations}")
    print()


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
        return (
            f"api_endpoints={details.get('api_endpoints') or []}, "
            f"graphql_endpoints={details.get('graphql_endpoints') or []}"
        )
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


def test_reqres_real_site_interaction_report() -> None:
    """End-to-end: collect real evidence, evaluate it, render a PDF report.

    Chains the existing `EvidenceCollectorAgent` into the existing
    `InteractionAgent` against a live website that actually exposes
    machine-readable interaction surfaces (REST endpoints + API docs),
    unlike the mytek.tn scenario, which scores 0. Requires network access.
    """
    evidence = EvidenceCollectorAgent().collect(TARGET_URL)
    result = InteractionAgent().evaluate(evidence)
    _print_result(f"real site: {TARGET_URL}", result)

    _generate_pdf_report(TARGET_URL, result, REPORT_PATH)
    _print_console_summary(TARGET_URL, result, REPORT_PATH)

    assert REPORT_PATH.exists()
    assert 0.0 <= result.score <= 100.0
    assert len(result.checks) == 6
    # Unlike mytek.tn, this site exposes real API endpoints and docs.
    assert result.score > 0.0
    assert result.checks["api_availability"] is True
    assert result.checks["api_documentation"] is True


if __name__ == "__main__":
    test_reqres_real_site_interaction_report()
    print("All tests passed.")

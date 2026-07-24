"""Unit tests for :class:`ComprehensionAgent`.

Covers a fully semantic website, a website with only basic metadata,
each individual criterion failing in isolation, and a website with
nothing comprehensible at all. The agent consumes only a
`WebsiteEvidence` instance built by hand here — no network access,
HTML parsing, or structured-data extraction tool is exercised by
these tests.
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

from agents.comprehension_agent import ComprehensionAgent
from agents.evidence_collector import EvidenceCollectorAgent
from models.comprehension import ComprehensionResult
from models.evidence import WebsiteEvidence

URL = "https://www.example.com"


def _print_result(label: str, result) -> None:
    print(f"--- {label} ---")
    print(f"score:           {result.score}")
    print(f"checks:          {result.checks}")
    print(f"details:         {result.details}")
    print(f"issues:          {result.issues}")
    print(f"recommendations: {result.recommendations}")
    print()


def _fully_semantic_evidence() -> WebsiteEvidence:
    """Build a `WebsiteEvidence` that should pass every criterion."""
    return WebsiteEvidence(
        url=URL,
        status_code=200,
        title="Example Site",
        meta_tags={"description": "A sample site for testing."},
        language="en",
        open_graph={"og:title": "Example Site", "og:image": "https://www.example.com/logo.png"},
        internal_links=["https://www.example.com/about", "https://www.example.com/contact"],
        structured_data={
            "json-ld": [
                {"@type": "Organization", "name": "Example Site"},
                {"@type": "Product", "name": "Widget"},
            ],
            "microdata": [],
            "rdfa": [],
        },
    )


def test_fully_semantic_website_scores_100() -> None:
    """Every criterion passes: the score should be exactly 100."""
    agent = ComprehensionAgent()

    result = agent.evaluate(_fully_semantic_evidence())
    _print_result("fully semantic website", result)

    assert result.score == 100.0
    assert all(result.checks.values())
    assert result.issues == []
    assert result.recommendations == []
    assert result.details["schema_types"] == ["Organization", "Product"]
    assert result.details["language"] == "en"


def test_only_basic_metadata_scores_partially() -> None:
    """Only metadata, Open Graph, and internal links exist: partial score."""
    agent = ComprehensionAgent()
    evidence = WebsiteEvidence(
        url=URL,
        title="Example Site",
        meta_tags={"description": "A sample site for testing."},
        language="en",
        open_graph={"og:title": "Example Site"},
        internal_links=["https://www.example.com/about"],
    )

    result = agent.evaluate(evidence)
    _print_result("only basic metadata", result)

    assert result.checks["structured_data"] is False
    assert result.checks["json_ld"] is False
    assert result.checks["schema_entities"] is False
    assert result.checks["metadata"] is True
    assert result.checks["semantic_formats"] is False
    assert result.checks["open_graph"] is True
    assert result.checks["internal_structure"] is True
    assert 0.0 < result.score < 100.0


def test_no_structured_data() -> None:
    """No structured data of any format: only that criterion (and
    downstream criteria relying on it) fail."""
    agent = ComprehensionAgent()
    evidence = _fully_semantic_evidence()
    evidence.structured_data = {}

    result = agent.evaluate(evidence)
    _print_result("no structured data", result)

    assert result.checks["structured_data"] is False
    assert "No structured data found" in result.issues


def test_missing_json_ld() -> None:
    """JSON-LD absent but other structured data present: json_ld fails."""
    agent = ComprehensionAgent()
    evidence = _fully_semantic_evidence()
    evidence.structured_data = {
        "json-ld": [],
        "microdata": [{"type": "https://schema.org/Product", "properties": {}}],
        "rdfa": [],
    }

    result = agent.evaluate(evidence)
    _print_result("missing JSON-LD", result)

    assert result.checks["json_ld"] is False
    assert "No JSON-LD semantic information found" in result.issues
    assert result.checks["structured_data"] is True
    assert result.checks["semantic_formats"] is True


def test_missing_metadata() -> None:
    """Title, description, and language all absent: metadata fails."""
    agent = ComprehensionAgent()
    evidence = _fully_semantic_evidence()
    evidence.title = None
    evidence.meta_tags = {}
    evidence.language = None

    result = agent.evaluate(evidence)
    _print_result("missing metadata", result)

    assert result.checks["metadata"] is False
    assert any("Missing metadata information" in issue for issue in result.issues)


def test_everything_missing_scores_near_zero() -> None:
    """A bare, empty evidence record should score at (or near) zero."""
    agent = ComprehensionAgent()
    evidence = WebsiteEvidence(url=URL)

    result = agent.evaluate(evidence)
    _print_result("everything missing", result)

    assert result.score == 0.0
    assert all(passed is False for passed in result.checks.values())
    assert len(result.issues) == 7
    assert len(result.recommendations) == 7


# ---------------------------------------------------------------------------
# End-to-end scenario: real website -> Evidence Collector -> Comprehension
# Agent -> PDF report.
#
# This section adds no logic to either agent; it only orchestrates the two
# existing components and renders their output. Mirrors the equivalent
# scenario in test_discoverability_agent.py.
# ---------------------------------------------------------------------------

TARGET_URL = "https://www.mytek.tn"
REPORT_PATH = Path(__file__).resolve().parent.parent / "comprehension_report_mytek.pdf"

# Maps each `ComprehensionResult.checks` key to its human-readable label,
# used when rendering the criteria table in the PDF report.
_CRITERIA_LABELS: dict[str, str] = {
    "structured_data": "Structured data availability",
    "json_ld": "JSON-LD semantic understanding",
    "schema_entities": "Schema.org entity description",
    "metadata": "Metadata completeness",
    "semantic_formats": "Content representation formats",
    "open_graph": "Open Graph semantic information",
    "internal_structure": "Internal content structure",
}


def _criterion_detail_summary(name: str, details: dict[str, Any]) -> str:
    """Summarize the supporting evidence for a single criterion.

    Args:
        name: The criterion's key in `ComprehensionResult.checks`.
        details: The full `ComprehensionResult.details` mapping.

    Returns:
        A short, human-readable description of the evidence backing
        this criterion's pass/fail outcome.
    """
    if name == "structured_data":
        return (
            f"json-ld={details.get('json_ld_found')}, "
            f"microdata={details.get('microdata_found')}, "
            f"rdfa={details.get('rdfa_found')}"
        )
    if name == "json_ld":
        return f"types={details.get('json_ld_types') or []}"
    if name == "schema_entities":
        return f"schema_types={details.get('schema_types') or []}"
    if name == "metadata":
        return (
            f"title={bool(details.get('title'))}, "
            f"description={details.get('has_description')}, "
            f"language={details.get('language')}"
        )
    if name == "semantic_formats":
        return f"formats={details.get('semantic_formats_found') or []}"
    if name == "open_graph":
        return f"tags={len(details.get('open_graph_tags') or [])}"
    if name == "internal_structure":
        return f"count={details.get('internal_links_count')}"
    return ""


def _generate_pdf_report(
    url: str, result: ComprehensionResult, output_path: Path
) -> None:
    """Render a `ComprehensionResult` as a PDF report.

    Args:
        url: The website URL that was assessed.
        result: The evaluation produced by `ComprehensionAgent.evaluate`.
        output_path: Filesystem path the PDF should be written to.
    """
    styles = getSampleStyleSheet()
    heading_style = ParagraphStyle(
        "SectionHeading", parent=styles["Heading2"], spaceBefore=12, spaceAfter=6
    )

    passed_count = sum(1 for outcome in result.checks.values() if outcome)
    failed_count = len(result.checks) - passed_count

    story: list[Any] = [
        Paragraph("ARAS Comprehension Assessment Report", styles["Title"]),
        Spacer(1, 0.5 * cm),
        Paragraph(f"<b>Website URL:</b> {url}", styles["Normal"]),
        Paragraph(
            f"<b>Analysis date:</b> {datetime.now(timezone.utc).isoformat()}",
            styles["Normal"],
        ),
        Paragraph("<b>Agent used:</b> Comprehension Agent", styles["Normal"]),
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
        f"JSON-LD present: {details.get('json_ld_found')}",
        f"Microdata present: {details.get('microdata_found')}",
        f"RDFa present: {details.get('rdfa_found')}",
        f"Schema.org types: {details.get('schema_types') or []}",
        f"Title: {details.get('title')}",
        f"Language: {details.get('language')}",
        f"Open Graph tags: {details.get('open_graph_tags') or []}",
        f"Semantic formats found: {details.get('semantic_formats_found') or []}",
        f"Internal links: {details.get('internal_links_count')}",
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


def _print_console_summary(url: str, result: ComprehensionResult, report_path: Path) -> None:
    """Print the human-facing summary of a real-site assessment run.

    Args:
        url: The website URL that was assessed.
        result: The evaluation produced by `ComprehensionAgent.evaluate`.
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
    print("ARAS Comprehension Report")
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


def test_mytek_real_site_comprehension_report() -> None:
    """End-to-end: collect real evidence, evaluate it, render a PDF report.

    Chains the existing `EvidenceCollectorAgent` into the existing
    `ComprehensionAgent` against a live website, then renders the
    resulting `ComprehensionResult` as a PDF. Requires network access.
    """
    evidence = EvidenceCollectorAgent().collect(TARGET_URL)
    result = ComprehensionAgent().evaluate(evidence)
    _print_result(f"real site: {TARGET_URL}", result)

    _generate_pdf_report(TARGET_URL, result, REPORT_PATH)
    _print_console_summary(TARGET_URL, result, REPORT_PATH)

    assert REPORT_PATH.exists()
    assert 0.0 <= result.score <= 100.0
    assert len(result.checks) == 7


if __name__ == "__main__":
    test_fully_semantic_website_scores_100()
    test_only_basic_metadata_scores_partially()
    test_no_structured_data()
    test_missing_json_ld()
    test_missing_metadata()
    test_everything_missing_scores_near_zero()
    test_mytek_real_site_comprehension_report()
    print("All tests passed.")

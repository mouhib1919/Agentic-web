"""Tests for :class:`ScoringAgent`.

Per the task requirements, this suite does not use artificial
scenarios: it runs the real `ARASOrchestrator` (Evidence Collector +
all four analysis agents) against `https://www.mytek.tn`, feeds the
resulting `DiscoverabilityResult` / `ComprehensionResult` /
`InteractionResult` / `SecurityResult` into `ScoringAgent.calculate()`,
and verifies the aggregated `GlobalReadinessResult`. It then renders a
consolidated PDF report ("ARAS Global Readiness Assessment Report").

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

from agents.scoring_agent import ScoringAgent
from models.scoring import GlobalReadinessResult
from orchestrator.agent import ARASOrchestrator

TARGET_URL = "https://www.mytek.tn"
REPORT_PATH = Path(__file__).resolve().parent.parent / "scoring_report_mytek.pdf"

_DIMENSION_LABELS: dict[str, str] = {
    "discoverability": "Discoverability",
    "comprehension": "Comprehension",
    "interaction": "Interaction",
    "security": "Security",
}


def _readiness_level(global_score: float) -> str:
    """Classify a global score into a human-facing readiness level.

    This classification is presentation-only: it belongs to the test's
    PDF rendering, not to `ScoringAgent`, which only aggregates scores.

    Args:
        global_score: The `GlobalReadinessResult.global_score` value.

    Returns:
        A short readiness-level label.
    """
    if global_score >= 80.0:
        return "Excellent"
    if global_score >= 60.0:
        return "Good"
    if global_score >= 40.0:
        return "Fair"
    if global_score >= 20.0:
        return "Poor"
    return "Critical"


def _print_result(label: str, result: GlobalReadinessResult) -> None:
    print(f"--- {label} ---")
    print(f"global_score:      {result.global_score}")
    print(f"dimension_scores:  {result.dimension_scores}")
    print(f"critical_issues:   {result.critical_issues}")
    print(f"recommendations:   {result.recommendations}")
    print()


def test_mytek_global_readiness_scoring() -> None:
    """Run the real ARAS workflow on mytek.tn and score its results.

    Workflow (per the task spec):
        1. Run ARAS Orchestrator on mytek.tn.
        2. Retrieve DiscoverabilityResult / ComprehensionResult /
           InteractionResult / SecurityResult from the resulting state.
        3. Send these results to ScoringAgent.
        4. Generate a GlobalReadinessResult.
        5. Verify global_score exists, dimension_scores contains all
           four dimensions, and issues/recommendations are aggregated.
    """
    state = ARASOrchestrator().run(TARGET_URL)

    discoverability_result = state["discoverability_result"]
    comprehension_result = state["comprehension_result"]
    interaction_result = state["interaction_result"]
    security_result = state["security_result"]

    assert discoverability_result is not None
    assert comprehension_result is not None
    assert interaction_result is not None
    assert security_result is not None

    result = ScoringAgent().calculate(
        discoverability_result=discoverability_result,
        comprehension_result=comprehension_result,
        interaction_result=interaction_result,
        security_result=security_result,
    )
    _print_result(f"ARAS Global Readiness Score: {TARGET_URL}", result)

    # global_score exists and is a valid percentage.
    assert isinstance(result.global_score, float)
    assert 0.0 <= result.global_score <= 100.0

    # dimension_scores contains exactly the four dimensions.
    assert set(result.dimension_scores.keys()) == set(_DIMENSION_LABELS.keys())
    for dimension, expected_result in (
        ("discoverability", discoverability_result),
        ("comprehension", comprehension_result),
        ("interaction", interaction_result),
        ("security", security_result),
    ):
        assert result.dimension_scores[dimension] == expected_result.score

    # The global score is the equally-weighted average of the four.
    expected_global_score = round(sum(result.dimension_scores.values()) / 4, 2)
    assert result.global_score == expected_global_score

    # Issues and recommendations are aggregated across all dimensions.
    all_source_issues = (
        discoverability_result.issues
        + comprehension_result.issues
        + interaction_result.issues
        + security_result.issues
    )
    all_source_recommendations = (
        discoverability_result.recommendations
        + comprehension_result.recommendations
        + interaction_result.recommendations
        + security_result.recommendations
    )
    assert set(result.critical_issues) <= set(all_source_issues)
    assert set(result.recommendations) <= set(all_source_recommendations)
    # No duplicates: every failed criterion across all four dimensions
    # is represented, but never more than once.
    assert len(result.critical_issues) == len(set(result.critical_issues))
    assert len(result.recommendations) == len(set(result.recommendations))
    if all_source_issues:
        assert result.critical_issues != []
    if all_source_recommendations:
        assert result.recommendations != []

    # details carries over each dimension's checks for a future
    # Reporter Agent to explain the global score.
    assert result.details["discoverability_checks"] == discoverability_result.checks
    assert result.details["comprehension_checks"] == comprehension_result.checks
    assert result.details["interaction_checks"] == interaction_result.checks
    assert result.details["security_checks"] == security_result.checks

    _generate_pdf_report(TARGET_URL, result, REPORT_PATH)
    _print_console_summary(TARGET_URL, result, REPORT_PATH)

    assert REPORT_PATH.exists()


# ---------------------------------------------------------------------------
# PDF report generation.
#
# Deliberately kept out of ScoringAgent (aggregation-only, per the task
# spec) — this is presentation logic that belongs to the test/report layer.
# ---------------------------------------------------------------------------


def _generate_pdf_report(url: str, result: GlobalReadinessResult, output_path: Path) -> None:
    """Render a `GlobalReadinessResult` as a professional PDF report.

    Args:
        url: The website URL that was assessed.
        result: The aggregate produced by `ScoringAgent.calculate`.
        output_path: Filesystem path the PDF should be written to.
    """
    styles = getSampleStyleSheet()
    heading_style = ParagraphStyle(
        "SectionHeading", parent=styles["Heading2"], spaceBefore=12, spaceAfter=6
    )
    sub_heading_style = ParagraphStyle(
        "SubHeading", parent=styles["Heading3"], spaceBefore=8, spaceAfter=4
    )

    readiness_level = _readiness_level(result.global_score)

    story: list[Any] = [
        Paragraph("ARAS Global Readiness Assessment Report", styles["Title"]),
        Spacer(1, 0.5 * cm),
        Paragraph(f"<b>Website:</b> {url}", styles["Normal"]),
        Paragraph(
            f"<b>Analysis date:</b> {datetime.now(timezone.utc).isoformat()}",
            styles["Normal"],
        ),
    ]

    # Section 1: Executive summary
    story.append(Paragraph("1. Executive Summary", heading_style))
    story.append(
        Paragraph(f"<b>Global Score:</b> {result.global_score}/100", styles["Normal"])
    )
    story.append(Paragraph(f"<b>Readiness Level:</b> {readiness_level}", styles["Normal"]))

    # Section 2: Dimension scores
    story.append(Paragraph("2. Dimension Scores", heading_style))
    dimension_rows = [["Dimension", "Score"]]
    for key, label in _DIMENSION_LABELS.items():
        dimension_rows.append([label, f"{result.dimension_scores.get(key, 0.0)}/100"])

    dimension_table = Table(dimension_rows, colWidths=[8 * cm, 6 * cm])
    dimension_table.setStyle(
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
    story.append(dimension_table)

    # Section 3: Detailed findings
    story.append(Paragraph("3. Detailed Findings", heading_style))
    for key, label in _DIMENSION_LABELS.items():
        story.append(Paragraph(label, sub_heading_style))
        story.append(
            Paragraph(f"<b>Score:</b> {result.dimension_scores.get(key, 0.0)}/100", styles["Normal"])
        )

        checks = result.details.get(f"{key}_checks", {})
        passed = [name for name, ok in checks.items() if ok]
        failed = [name for name, ok in checks.items() if not ok]

        story.append(Paragraph(f"<b>Passed checks:</b> {', '.join(passed) or 'none'}", styles["Normal"]))
        story.append(Paragraph(f"<b>Failed checks:</b> {', '.join(failed) or 'none'}", styles["Normal"]))

    # Section 4: Critical issues
    story.append(Paragraph("4. Critical Issues", heading_style))
    if result.critical_issues:
        story.append(
            ListFlowable(
                [ListItem(Paragraph(issue, styles["Normal"])) for issue in result.critical_issues],
                bulletType="bullet",
            )
        )
    else:
        story.append(Paragraph("No critical issues found.", styles["Normal"]))

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


def _print_console_summary(
    url: str, result: GlobalReadinessResult, report_path: Path
) -> None:
    """Print the human-facing summary of a real-site scoring run.

    Args:
        url: The website URL that was assessed.
        result: The aggregate produced by `ScoringAgent.calculate`.
        report_path: Filesystem path the PDF report was written to.
    """
    print("=" * 40)
    print("ARAS Global Readiness Score")
    print()
    print(f"Website: {url}")
    print()
    print("Dimension Scores:")
    for key, label in _DIMENSION_LABELS.items():
        print(f"  {label}: {result.dimension_scores.get(key, 0.0)}")
    print()
    print(f"Global Score: {result.global_score} / 100")
    print(f"Readiness Level: {_readiness_level(result.global_score)}")
    print()
    print("Critical Issues:")
    for issue in result.critical_issues:
        print(f"  - {issue}")
    print()
    print("Recommendations:")
    for recommendation in result.recommendations:
        print(f"  - {recommendation}")
    print()
    print("PDF generated:")
    print(report_path)
    print("=" * 40)


if __name__ == "__main__":
    test_mytek_global_readiness_scoring()
    print("All tests passed.")

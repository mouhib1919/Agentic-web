"""Tests for :class:`ARASOrchestrator`.

Covers, using a fake Evidence Collector (no real network access): the
full graph wiring a website through all four analysis agents, evidence
collection failing outright, and a single analysis agent failing in
isolation without aborting the rest of the workflow.

It also includes an end-to-end scenario against a real website
(`https://www.mytek.tn`) that runs the orchestrator against the live
Evidence Collector and every real analysis agent, then renders the
resulting `ARASState` as a single consolidated PDF report, mirroring
the per-agent real-site scenarios already used for Discoverability,
Comprehension, Interaction, and Security.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch

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

from models.evidence import WebsiteEvidence
from orchestrator.agent import ARASOrchestrator
from orchestrator.state import ARASState

URL = "https://www.example.com"


def _print_state(label: str, state: ARASState) -> None:
    print(f"--- {label} ---")
    print(f"url:                     {state['url']}")
    print(f"evidence collected:      {state['evidence'] is not None}")
    print(f"discoverability_result:  {state['discoverability_result']}")
    print(f"comprehension_result:    {state['comprehension_result']}")
    print(f"interaction_result:      {state['interaction_result']}")
    print(f"security_result:         {state['security_result']}")
    print(f"errors:                  {state['errors']}")
    print()


def _fake_evidence() -> WebsiteEvidence:
    """Build a minimal `WebsiteEvidence` sufficient for every analysis agent."""
    return WebsiteEvidence(
        url=URL,
        status_code=200,
        title="Example Site",
        language="en",
        meta_tags={"description": "A sample site for testing."},
        canonical="https://www.example.com/",
        open_graph={"og:title": "Example Site"},
        internal_links=["https://www.example.com/about"],
        robots_txt="User-agent: *",
        sitemap_xml="<urlset></urlset>",
        llms_txt="# Example",
        structured_data={"json-ld": [{"@type": "Organization"}], "microdata": [], "rdfa": []},
        api_analysis={"api_endpoints": ["https://www.example.com/api"]},
        headers={"Strict-Transport-Security": "max-age=31536000", "Server": "cloudflare"},
    )


def test_full_workflow_runs_all_agents() -> None:
    """A successful collection is distributed to all four analysis agents."""
    with patch(
        "orchestrator.nodes.EvidenceCollectorAgent.collect", return_value=_fake_evidence()
    ):
        orchestrator = ARASOrchestrator()
        state = orchestrator.run(URL)

    _print_state("full workflow", state)

    assert state["url"] == URL
    assert isinstance(state["evidence"], WebsiteEvidence)
    assert state["discoverability_result"] is not None
    assert state["comprehension_result"] is not None
    assert state["interaction_result"] is not None
    assert state["security_result"] is not None
    assert state["errors"] == []


def test_evidence_collection_failure_is_recorded() -> None:
    """Evidence collection raising is recorded in `errors`; graph does not crash."""
    with patch(
        "orchestrator.nodes.EvidenceCollectorAgent.collect",
        side_effect=RuntimeError("simulated network failure"),
    ):
        orchestrator = ARASOrchestrator()
        state = orchestrator.run(URL)

    _print_state("evidence collection failure", state)

    assert state["evidence"] is None
    assert state["discoverability_result"] is None
    assert state["comprehension_result"] is None
    assert state["interaction_result"] is None
    assert state["security_result"] is None
    assert any("evidence_collector" in error for error in state["errors"])
    assert any("no evidence available" in error for error in state["errors"])


def test_single_agent_failure_does_not_abort_workflow() -> None:
    """One analysis agent raising does not prevent the others from completing."""
    with patch(
        "orchestrator.nodes.EvidenceCollectorAgent.collect", return_value=_fake_evidence()
    ), patch(
        "orchestrator.nodes.SecurityAgent.evaluate",
        side_effect=RuntimeError("simulated security agent failure"),
    ):
        orchestrator = ARASOrchestrator()
        state = orchestrator.run(URL)

    _print_state("single agent failure (security)", state)

    assert state["discoverability_result"] is not None
    assert state["comprehension_result"] is not None
    assert state["interaction_result"] is not None
    assert state["security_result"] is None
    assert any("security_result" in error for error in state["errors"])


# ---------------------------------------------------------------------------
# End-to-end scenario: real website -> ARASOrchestrator (Evidence Collector +
# all four analysis agents) -> PDF report.
#
# This section adds no logic to the orchestrator or any agent; it only runs
# the existing workflow and renders its output, mirroring the real-site
# scenarios already used for the individual agents.
# ---------------------------------------------------------------------------

TARGET_URL = "https://www.mytek.tn"
REPORT_PATH = Path(__file__).resolve().parent.parent / "orchestrator_report_mytek.pdf"

_AGENT_SECTIONS: list[tuple[str, str]] = [
    ("discoverability_result", "Discoverability"),
    ("comprehension_result", "Comprehension"),
    ("interaction_result", "Interaction"),
    ("security_result", "Security"),
]


def _generate_pdf_report(url: str, state: ARASState, output_path: Path) -> None:
    """Render a full `ARASState` as a single consolidated PDF report.

    Args:
        url: The website URL that was assessed.
        state: The final state produced by `ARASOrchestrator.run`.
        output_path: Filesystem path the PDF should be written to.
    """
    styles = getSampleStyleSheet()
    heading_style = ParagraphStyle(
        "SectionHeading", parent=styles["Heading2"], spaceBefore=12, spaceAfter=6
    )
    sub_heading_style = ParagraphStyle(
        "SubHeading", parent=styles["Heading3"], spaceBefore=8, spaceAfter=4
    )

    story: list[Any] = [
        Paragraph("ARAS Orchestrator Assessment Report", styles["Title"]),
        Spacer(1, 0.5 * cm),
        Paragraph(f"<b>Website URL:</b> {url}", styles["Normal"]),
        Paragraph(
            f"<b>Analysis date:</b> {datetime.now(timezone.utc).isoformat()}",
            styles["Normal"],
        ),
        Paragraph(
            "<b>Workflow:</b> Evidence Collector -> "
            "[Discoverability, Comprehension, Interaction, Security] (parallel)",
            styles["Normal"],
        ),
    ]

    # Section 1: Evidence overview
    story.append(Paragraph("1. Evidence Overview", heading_style))
    evidence = state.get("evidence")
    if evidence is not None:
        overview_lines = [
            f"Status code: {evidence.status_code}",
            f"Title: {evidence.title}",
            f"Collection errors: {len(evidence.errors)}",
        ]
    else:
        overview_lines = ["Evidence collection failed; no evidence available."]
    story.append(
        ListFlowable(
            [ListItem(Paragraph(line, styles["Normal"])) for line in overview_lines],
            bulletType="bullet",
        )
    )

    # Section 2: Per-agent scores summary table
    story.append(Paragraph("2. Agent Scores Summary", heading_style))
    summary_rows = [["Agent", "Score", "Status"]]
    for key, label in _AGENT_SECTIONS:
        result = state.get(key)
        score = f"{result.score}/100" if result is not None else "N/A"
        status = "OK" if result is not None else "FAILED"
        summary_rows.append([label, score, status])

    summary_table = Table(summary_rows, colWidths=[6 * cm, 4 * cm, 4 * cm])
    summary_table.setStyle(
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
    story.append(summary_table)

    # Section 3: Per-agent detail
    story.append(Paragraph("3. Agent Details", heading_style))
    for key, label in _AGENT_SECTIONS:
        result = state.get(key)
        story.append(Paragraph(label, sub_heading_style))
        if result is None:
            story.append(Paragraph("This agent did not produce a result.", styles["Normal"]))
            continue

        story.append(Paragraph(f"<b>Score:</b> {result.score}/100", styles["Normal"]))
        checks_rows = [["Criterion", "Status"]]
        for name, passed in result.checks.items():
            checks_rows.append([name, "PASS" if passed else "FAIL"])
        checks_table = Table(checks_rows, colWidths=[9 * cm, 5 * cm])
        checks_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4C566A")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                ]
            )
        )
        story.append(checks_table)

        if result.issues:
            story.append(
                ListFlowable(
                    [ListItem(Paragraph(issue, styles["Normal"])) for issue in result.issues],
                    bulletType="bullet",
                )
            )
        else:
            story.append(Paragraph("No issues found.", styles["Normal"]))

    # Section 4: Workflow errors
    story.append(Paragraph("4. Workflow Errors", heading_style))
    if state["errors"]:
        story.append(
            ListFlowable(
                [ListItem(Paragraph(error, styles["Normal"])) for error in state["errors"]],
                bulletType="bullet",
            )
        )
    else:
        story.append(Paragraph("No workflow errors.", styles["Normal"]))

    SimpleDocTemplate(str(output_path), pagesize=A4).build(story)


def _print_console_summary(url: str, state: ARASState, report_path: Path) -> None:
    """Print the human-facing summary of a real-site orchestrator run.

    Args:
        url: The website URL that was assessed.
        state: The final state produced by `ARASOrchestrator.run`.
        report_path: Filesystem path the PDF report was written to.
    """
    print("=" * 30)
    print("ARAS Orchestrator Report")
    print(f"Website: {url}")
    print()
    for key, label in _AGENT_SECTIONS:
        result = state.get(key)
        score = f"{result.score}/100" if result is not None else "FAILED"
        print(f"{label}: {score}")
    print()
    print(f"Workflow errors: {state['errors']}")
    print()
    print("PDF generated:")
    print(report_path)
    print("=" * 30)


def test_mytek_real_site_orchestrator_report() -> None:
    """End-to-end: run the full ARAS workflow against mytek.tn, render a PDF.

    Runs the real `EvidenceCollectorAgent` and every real analysis
    agent through the compiled LangGraph workflow, then renders the
    resulting `ARASState` as a PDF. Requires network access.
    """
    orchestrator = ARASOrchestrator()
    state = orchestrator.run(TARGET_URL)
    _print_state(f"real site: {TARGET_URL}", state)

    _generate_pdf_report(TARGET_URL, state, REPORT_PATH)
    _print_console_summary(TARGET_URL, state, REPORT_PATH)

    assert REPORT_PATH.exists()
    assert state["evidence"] is not None
    assert state["discoverability_result"] is not None
    assert state["comprehension_result"] is not None
    assert state["interaction_result"] is not None
    assert state["security_result"] is not None


if __name__ == "__main__":
    test_full_workflow_runs_all_agents()
    test_evidence_collection_failure_is_recorded()
    test_single_agent_failure_does_not_abort_workflow()
    test_mytek_real_site_orchestrator_report()
    print("All tests passed.")

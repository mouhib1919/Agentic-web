"""End-to-end test of :class:`EvidenceCollectorAgent` against a real website.

Chains the existing `EvidenceCollectorAgent` against `https://www.mytek.tn`
and renders the raw `WebsiteEvidence` snapshot as a PDF report. This adds no
logic to the agent; it only orchestrates the existing component and renders
its output, mirroring the real-site scenarios already used for the
Discoverability, Comprehension, and Interaction agents. The Evidence
Collector performs no scoring or judgment, so this report presents raw
collected facts rather than checks/issues/recommendations.

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
from models.evidence import WebsiteEvidence

TARGET_URL = "https://www.mytek.tn"
REPORT_PATH = Path(__file__).resolve().parent.parent / "evidence_collector_report_mytek.pdf"


def _print_evidence(label: str, evidence: WebsiteEvidence) -> None:
    print(f"--- {label} ---")
    print(f"url:                {evidence.url}")
    print(f"status_code:        {evidence.status_code}")
    print(f"response_time:      {evidence.response_time}")
    print(f"title:              {evidence.title}")
    print(f"language:           {evidence.language}")
    print(f"canonical:          {evidence.canonical}")
    print(f"meta_tags:          {evidence.meta_tags}")
    print(f"open_graph:         {evidence.open_graph}")
    print(f"html (len):         {len(evidence.html) if evidence.html else 0}")
    print(f"javascript_files:   {len(evidence.javascript_files)}")
    print(f"css_files:          {len(evidence.css_files)}")
    print(f"internal_links:     {len(evidence.internal_links)}")
    print(f"external_links:     {len(evidence.external_links)}")
    print(f"structured_data:    {evidence.structured_data}")
    print(f"robots_txt (len):   {len(evidence.robots_txt) if evidence.robots_txt else 0}")
    print(f"sitemap_xml (len):  {len(evidence.sitemap_xml) if evidence.sitemap_xml else 0}")
    print(f"llms_txt:           {evidence.llms_txt}")
    print(f"api_analysis:       {evidence.api_analysis}")
    print(f"api_candidates:     {evidence.api_candidates}")
    print(f"frontend_analysis:  {evidence.frontend_analysis}")
    print(f"errors:             {evidence.errors}")
    print()


def _generate_pdf_report(url: str, evidence: WebsiteEvidence, output_path: Path) -> None:
    """Render a `WebsiteEvidence` snapshot as a PDF report.

    Args:
        url: The website URL that was collected.
        evidence: The raw evidence produced by `EvidenceCollectorAgent.collect`.
        output_path: Filesystem path the PDF should be written to.
    """
    styles = getSampleStyleSheet()
    heading_style = ParagraphStyle(
        "SectionHeading", parent=styles["Heading2"], spaceBefore=12, spaceAfter=6
    )

    story: list[Any] = [
        Paragraph("ARAS Evidence Collector Report", styles["Title"]),
        Spacer(1, 0.5 * cm),
        Paragraph(f"<b>Website URL:</b> {url}", styles["Normal"]),
        Paragraph(
            f"<b>Analysis date:</b> {datetime.now(timezone.utc).isoformat()}",
            styles["Normal"],
        ),
        Paragraph("<b>Agent used:</b> Evidence Collector Agent", styles["Normal"]),
    ]

    # Section 1: Homepage overview
    story.append(Paragraph("1. Homepage Overview", heading_style))
    overview_rows = [
        ["Field", "Value"],
        ["Status code", str(evidence.status_code)],
        ["Response time (s)", str(evidence.response_time)],
        ["Title", str(evidence.title)],
        ["Language", str(evidence.language)],
        ["Canonical", str(evidence.canonical)],
        ["HTML size (chars)", str(len(evidence.html) if evidence.html else 0)],
    ]
    overview_table = Table(overview_rows, colWidths=[5 * cm, 11 * cm])
    overview_table.setStyle(
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
    story.append(overview_table)

    # Section 2: Metadata and links
    story.append(Paragraph("2. Metadata and Navigation", heading_style))
    metadata_lines = [
        f"Meta description: {evidence.meta_tags.get('description')}",
        f"Open Graph tags: {list(evidence.open_graph.keys())}",
        f"Internal links found: {len(evidence.internal_links)}",
        f"External links found: {len(evidence.external_links)}",
        f"JavaScript files found: {len(evidence.javascript_files)}",
        f"CSS files found: {len(evidence.css_files)}",
    ]
    story.append(
        ListFlowable(
            [ListItem(Paragraph(line, styles["Normal"])) for line in metadata_lines],
            bulletType="bullet",
        )
    )

    # Section 3: Structured data
    story.append(Paragraph("3. Structured Data", heading_style))
    structured_data = evidence.structured_data
    structured_lines = [
        f"JSON-LD objects found: {len(structured_data.get('json-ld') or [])}",
        f"Microdata items found: {len(structured_data.get('microdata') or [])}",
        f"RDFa items found: {len(structured_data.get('rdfa') or [])}",
    ]
    story.append(
        ListFlowable(
            [ListItem(Paragraph(line, styles["Normal"])) for line in structured_lines],
            bulletType="bullet",
        )
    )

    # Section 4: Standard discovery resources
    story.append(Paragraph("4. Standard Discovery Resources", heading_style))
    resource_lines = [
        f"robots.txt found: {bool(evidence.robots_txt)}",
        f"sitemap.xml found: {bool(evidence.sitemap_xml)}",
        f"llms.txt found: {bool(evidence.llms_txt)}",
    ]
    story.append(
        ListFlowable(
            [ListItem(Paragraph(line, styles["Normal"])) for line in resource_lines],
            bulletType="bullet",
        )
    )

    # Section 5: API and frontend analysis
    story.append(Paragraph("5. API and Frontend Analysis", heading_style))
    api_analysis = evidence.api_analysis
    frontend_analysis = evidence.frontend_analysis
    api_lines = [
        f"OpenAPI URLs: {api_analysis.get('openapi_urls') or []}",
        f"Swagger URLs: {api_analysis.get('swagger_urls') or []}",
        f"API endpoints: {api_analysis.get('api_endpoints') or []}",
        f"GraphQL endpoints: {api_analysis.get('graphql_endpoints') or []}",
        f"MCP endpoints: {api_analysis.get('mcp_endpoints') or []}",
        f"Frontend API URLs discovered: {frontend_analysis.get('discovered_api_urls') or []}",
    ]
    story.append(
        ListFlowable(
            [ListItem(Paragraph(line, styles["Normal"])) for line in api_lines],
            bulletType="bullet",
        )
    )

    # Section 6: Collection errors
    story.append(Paragraph("6. Collection Errors", heading_style))
    if evidence.errors:
        error_lines = [f"[{error.step}] {error.message}" for error in evidence.errors]
        story.append(
            ListFlowable(
                [ListItem(Paragraph(line, styles["Normal"])) for line in error_lines],
                bulletType="bullet",
            )
        )
    else:
        story.append(Paragraph("No collection errors.", styles["Normal"]))

    SimpleDocTemplate(str(output_path), pagesize=A4).build(story)


def _print_console_summary(url: str, evidence: WebsiteEvidence, report_path: Path) -> None:
    """Print the human-facing summary of a real-site collection run.

    Args:
        url: The website URL that was collected.
        evidence: The raw evidence produced by `EvidenceCollectorAgent.collect`.
        report_path: Filesystem path the PDF report was written to.
    """
    print("=" * 30)
    print("ARAS Evidence Collector Report")
    print(f"Website: {url}")
    print()
    print(f"Status code: {evidence.status_code}")
    print(f"Title: {evidence.title}")
    print(f"Collection errors: {len(evidence.errors)}")
    print()
    print("PDF generated:")
    print(report_path)
    print("=" * 30)


def test_mytek_real_site_evidence_collection_report() -> None:
    """End-to-end: collect real evidence from mytek.tn and render a PDF report.

    Requires network access.
    """
    evidence = EvidenceCollectorAgent().collect(TARGET_URL)
    _print_evidence(f"real site: {TARGET_URL}", evidence)

    _generate_pdf_report(TARGET_URL, evidence, REPORT_PATH)
    _print_console_summary(TARGET_URL, evidence, REPORT_PATH)

    assert REPORT_PATH.exists()
    assert evidence.url == TARGET_URL
    assert evidence.status_code == 200


if __name__ == "__main__":
    test_mytek_real_site_evidence_collection_report()
    print("All tests passed.")

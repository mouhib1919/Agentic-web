"""Unit tests for :class:`SecurityAgent`.

Covers a fully secure website, each individual criterion failing in
isolation, and a website with no security posture at all. The agent
consumes only a `WebsiteEvidence` instance built by hand here — no
network access or header-discovery tool is exercised by these tests.

It also includes an end-to-end scenario against a real website
(`https://www.mytek.tn`) that chains the existing
`EvidenceCollectorAgent` into the `SecurityAgent` and renders the
outcome as a PDF report, mirroring the equivalent scenarios for the
Discoverability, Comprehension, and Interaction agents.
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
from agents.security_agent import SecurityAgent
from models.evidence import WebsiteEvidence
from models.security import SecurityResult

URL = "https://www.example.com"


def _print_result(label: str, result: SecurityResult) -> None:
    print(f"--- {label} ---")
    print(f"score:           {result.score}")
    print(f"checks:          {result.checks}")
    print(f"details:         {result.details}")
    print(f"issues:          {result.issues}")
    print(f"recommendations: {result.recommendations}")
    print()


def _fully_secure_evidence() -> WebsiteEvidence:
    """Build a `WebsiteEvidence` that should pass every criterion."""
    return WebsiteEvidence(
        url=URL,
        status_code=200,
        headers={
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'",
            "X-Frame-Options": "SAMEORIGIN",
            "X-Content-Type-Options": "nosniff",
            "X-XSS-Protection": "1; mode=block",
            "Server": "cloudflare",
        },
    )


def test_fully_secure_website_scores_100() -> None:
    """Every criterion passes: the score should be exactly 100."""
    agent = SecurityAgent()

    result = agent.evaluate(_fully_secure_evidence())
    _print_result("fully secure website", result)

    assert result.score == 100.0
    assert all(result.checks.values())
    assert result.issues == []
    assert result.recommendations == []
    assert result.details["server"] == "cloudflare"


def test_header_case_insensitivity() -> None:
    """Headers stored with unusual casing must still be recognized."""
    agent = SecurityAgent()
    evidence = _fully_secure_evidence()
    evidence.headers = {
        "STRICT-TRANSPORT-SECURITY": "max-age=31536000",
        "content-security-policy": "default-src 'self'",
        "X-frame-Options": "DENY",
        "x-CONTENT-type-options": "nosniff",
        "x-xss-protection": "0",
        "SERVER": "Cloudflare",
    }

    result = agent.evaluate(evidence)
    _print_result("case-insensitive headers", result)

    assert result.checks["hsts"] is True
    assert result.checks["csp"] is True
    assert result.checks["x_frame_options"] is True
    assert result.checks["mime_xss"] is True
    assert result.checks["infrastructure_security"] is True


def test_missing_https() -> None:
    """The URL uses plain HTTP: only that criterion fails."""
    agent = SecurityAgent()
    evidence = _fully_secure_evidence()
    evidence.url = "http://www.example.com"

    result = agent.evaluate(evidence)
    _print_result("missing HTTPS", result)

    assert result.checks["https"] is False
    assert "HTTPS is not enabled." in result.issues
    assert result.score == round(6 / 7 * 100, 2)


def test_missing_http_200() -> None:
    """The homepage did not respond with HTTP 200: only that criterion fails."""
    agent = SecurityAgent()
    evidence = _fully_secure_evidence()
    evidence.status_code = 503

    result = agent.evaluate(evidence)
    _print_result("missing HTTP 200", result)

    assert result.checks["http_status"] is False
    assert result.score == round(6 / 7 * 100, 2)


def test_missing_hsts() -> None:
    """HSTS header absent: only that criterion fails."""
    agent = SecurityAgent()
    evidence = _fully_secure_evidence()
    del evidence.headers["Strict-Transport-Security"]

    result = agent.evaluate(evidence)
    _print_result("missing HSTS", result)

    assert result.checks["hsts"] is False
    assert "No HSTS header detected." in result.issues
    assert result.score == round(6 / 7 * 100, 2)


def test_missing_csp() -> None:
    """CSP header absent: only that criterion fails."""
    agent = SecurityAgent()
    evidence = _fully_secure_evidence()
    del evidence.headers["Content-Security-Policy"]

    result = agent.evaluate(evidence)
    _print_result("missing CSP", result)

    assert result.checks["csp"] is False
    assert "Missing Content-Security-Policy header." in result.issues
    assert result.score == round(6 / 7 * 100, 2)


def test_missing_x_frame_options() -> None:
    """X-Frame-Options absent: only that criterion fails."""
    agent = SecurityAgent()
    evidence = _fully_secure_evidence()
    del evidence.headers["X-Frame-Options"]

    result = agent.evaluate(evidence)
    _print_result("missing X-Frame-Options", result)

    assert result.checks["x_frame_options"] is False
    assert "Missing X-Frame-Options header." in result.issues
    assert result.score == round(6 / 7 * 100, 2)


def test_missing_mime_and_xss_protection() -> None:
    """Both X-Content-Type-Options and X-XSS-Protection absent: criterion fails."""
    agent = SecurityAgent()
    evidence = _fully_secure_evidence()
    del evidence.headers["X-Content-Type-Options"]
    del evidence.headers["X-XSS-Protection"]

    result = agent.evaluate(evidence)
    _print_result("missing MIME/XSS protection", result)

    assert result.checks["mime_xss"] is False
    assert "Missing MIME/XSS protection headers." in result.issues
    assert result.score == round(6 / 7 * 100, 2)


def test_partial_mime_or_xss_protection_passes() -> None:
    """Only one of X-Content-Type-Options / X-XSS-Protection present: criterion passes."""
    agent = SecurityAgent()
    evidence = _fully_secure_evidence()
    del evidence.headers["X-XSS-Protection"]

    result = agent.evaluate(evidence)
    _print_result("partial MIME/XSS protection", result)

    assert result.checks["mime_xss"] is True
    assert result.score == 100.0


def test_no_infrastructure_security() -> None:
    """No recognized CDN/WAF/reverse proxy: only that criterion fails."""
    agent = SecurityAgent()
    evidence = _fully_secure_evidence()
    evidence.headers["Server"] = "nginx"

    result = agent.evaluate(evidence)
    _print_result("no infrastructure security", result)

    assert result.checks["infrastructure_security"] is False
    assert "No recognized reverse proxy, CDN, or WAF detected." in result.issues
    assert result.score == round(6 / 7 * 100, 2)


def test_infrastructure_detected_via_indicator_header_without_server_match() -> None:
    """A provider-specific header alone (masked Server header) still passes."""
    agent = SecurityAgent()
    evidence = _fully_secure_evidence()
    evidence.headers["Server"] = "unknown"
    evidence.headers["cf-ray"] = "8a1234567890abcd-CDG"

    result = agent.evaluate(evidence)
    _print_result("infrastructure via indicator header", result)

    assert result.checks["infrastructure_security"] is True


def test_no_header_duplication_across_criteria() -> None:
    """Each header contributes to exactly one criterion's outcome.

    Regression test: X-Frame-Options must not affect `mime_xss`, and
    the MIME/XSS headers must not affect `x_frame_options`.
    """
    agent = SecurityAgent()
    evidence = WebsiteEvidence(
        url=URL,
        status_code=200,
        headers={"X-Frame-Options": "DENY"},
    )

    result = agent.evaluate(evidence)
    _print_result("no header duplication", result)

    assert result.checks["x_frame_options"] is True
    assert result.checks["mime_xss"] is False

    evidence.headers = {"X-Content-Type-Options": "nosniff"}
    result = agent.evaluate(evidence)

    assert result.checks["mime_xss"] is True
    assert result.checks["x_frame_options"] is False


def test_everything_missing_scores_near_zero() -> None:
    """A bare, empty evidence record should score at (or near) zero."""
    agent = SecurityAgent()
    evidence = WebsiteEvidence(url="http://www.example.com")

    result = agent.evaluate(evidence)
    _print_result("everything missing", result)

    assert result.score == 0.0
    assert all(passed is False for passed in result.checks.values())
    assert len(result.issues) == 7
    assert len(result.recommendations) == 7


# ---------------------------------------------------------------------------
# End-to-end scenario: real website -> Evidence Collector -> Security Agent
# -> PDF report.
#
# This section adds no logic to either agent; it only orchestrates the two
# existing components and renders their output. Mirrors the equivalent
# scenarios in test_discoverability_agent.py / test_comprehension_agent.py /
# test_interaction_agent.py.
# ---------------------------------------------------------------------------

TARGET_URL = "https://www.mytek.tn"
REPORT_PATH = Path(__file__).resolve().parent.parent / "security_report_mytek.pdf"

# Maps each `SecurityResult.checks` key to its human-readable label, used
# when rendering the criteria table in the PDF report.
_CRITERIA_LABELS: dict[str, str] = {
    "https": "HTTPS",
    "http_status": "HTTP response status",
    "hsts": "Transport security (HSTS)",
    "csp": "Content Security Policy",
    "x_frame_options": "Clickjacking protection",
    "mime_xss": "MIME and XSS protection",
    "infrastructure_security": "Infrastructure security",
}


def _criterion_detail_summary(name: str, details: dict[str, Any]) -> str:
    """Summarize the supporting evidence for a single criterion.

    Args:
        name: The criterion's key in `SecurityResult.checks`.
        details: The full `SecurityResult.details` mapping.

    Returns:
        A short, human-readable description of the evidence backing
        this criterion's pass/fail outcome.
    """
    if name == "https":
        return f"url={details.get('url')}"
    if name == "http_status":
        return f"status_code={details.get('status_code')}"
    if name == "hsts":
        return f"present={details.get('hsts')}"
    if name == "csp":
        return f"present={details.get('content_security_policy')}"
    if name == "x_frame_options":
        return f"value={details.get('x_frame_options')}"
    if name == "mime_xss":
        return (
            f"x_content_type_options={details.get('x_content_type_options')}, "
            f"x_xss_protection={details.get('x_xss_protection')}"
        )
    if name == "infrastructure_security":
        return f"server={details.get('server')}"
    return ""


def _generate_pdf_report(url: str, result: SecurityResult, output_path: Path) -> None:
    """Render a `SecurityResult` as a PDF report.

    Args:
        url: The website URL that was assessed.
        result: The evaluation produced by `SecurityAgent.evaluate`.
        output_path: Filesystem path the PDF should be written to.
    """
    styles = getSampleStyleSheet()
    heading_style = ParagraphStyle(
        "SectionHeading", parent=styles["Heading2"], spaceBefore=12, spaceAfter=6
    )

    passed_count = sum(1 for outcome in result.checks.values() if outcome)
    failed_count = len(result.checks) - passed_count

    story: list[Any] = [
        Paragraph("ARAS Security Assessment Report", styles["Title"]),
        Spacer(1, 0.5 * cm),
        Paragraph(f"<b>Website URL:</b> {url}", styles["Normal"]),
        Paragraph(
            f"<b>Analysis date:</b> {datetime.now(timezone.utc).isoformat()}",
            styles["Normal"],
        ),
        Paragraph("<b>Agent used:</b> Security Agent", styles["Normal"]),
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
        f"URL: {details.get('url')}",
        f"Status code: {details.get('status_code')}",
        f"HSTS present: {details.get('hsts')}",
        f"CSP present: {details.get('content_security_policy')}",
        f"X-Frame-Options: {details.get('x_frame_options')}",
        f"X-Content-Type-Options: {details.get('x_content_type_options')}",
        f"X-XSS-Protection: {details.get('x_xss_protection')}",
        f"Server: {details.get('server')}",
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


def _print_console_summary(url: str, result: SecurityResult, report_path: Path) -> None:
    """Print the human-facing summary of a real-site assessment run.

    Args:
        url: The website URL that was assessed.
        result: The evaluation produced by `SecurityAgent.evaluate`.
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
    print("ARAS Security Report")
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


def test_mytek_real_site_security_report() -> None:
    """End-to-end: collect real evidence, evaluate it, render a PDF report.

    Chains the existing `EvidenceCollectorAgent` into the existing
    `SecurityAgent` against a live website, then renders the resulting
    `SecurityResult` as a PDF. Requires network access.
    """
    evidence = EvidenceCollectorAgent().collect(TARGET_URL)
    result = SecurityAgent().evaluate(evidence)
    _print_result(f"real site: {TARGET_URL}", result)

    _generate_pdf_report(TARGET_URL, result, REPORT_PATH)
    _print_console_summary(TARGET_URL, result, REPORT_PATH)

    assert REPORT_PATH.exists()
    assert 0.0 <= result.score <= 100.0
    assert len(result.checks) == 7


if __name__ == "__main__":
    test_fully_secure_website_scores_100()
    test_header_case_insensitivity()
    test_missing_https()
    test_missing_http_200()
    test_missing_hsts()
    test_missing_csp()
    test_missing_x_frame_options()
    test_missing_mime_and_xss_protection()
    test_partial_mime_or_xss_protection_passes()
    test_no_infrastructure_security()
    test_infrastructure_detected_via_indicator_header_without_server_match()
    test_no_header_duplication_across_criteria()
    test_everything_missing_scores_near_zero()
    test_mytek_real_site_security_report()
    print("All tests passed.")

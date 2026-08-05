"""Reporter Agent.

This module is the final rendering layer of ARAS. It takes every
already-computed result produced by earlier stages (evidence, the four
analysis results, the global score, the classified issues, and the
generated recommendations) and renders them into a single, professional
PDF report.

This agent MUST NOT:
    - collect evidence
    - analyze websites
    - calculate scores
    - classify issues or assign priorities
    - retrieve documents or call an LLM to generate recommendations

Those responsibilities belong to earlier ARAS layers. This agent only
formats and renders results that already exist; it recomputes nothing.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse
from xml.sax.saxutils import escape as _xml_escape

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

from models.comprehension import ComprehensionResult
from models.discoverability import DiscoverabilityResult
from models.evidence import WebsiteEvidence
from models.interaction import InteractionResult
from models.recommendation import RecommendationResult
from models.report import ReportResult
from models.rule_engine import RuleEngineResult
from models.scoring import GlobalReadinessResult
from models.security import SecurityResult

_REPORTS_DIRECTORY = "reports"
_REPORT_FILENAME_SUFFIX = "_aras_report.pdf"
_PRIORITY_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}

_DIMENSION_LABELS: dict[str, str] = {
    "discoverability": "Discoverability",
    "comprehension": "Comprehension",
    "interaction": "Interaction",
    "security": "Security",
}


class ReporterAgent:
    """Renders every already-computed ARAS result into a single PDF report.

    This class holds no analysis, scoring, classification, or
    recommendation-generation logic. It is a pure formatting/rendering
    step: structured results in, a PDF file on disk out.
    """

    def generate(
        self,
        url: str,
        evidence: Optional[WebsiteEvidence],
        discoverability_result: Optional[DiscoverabilityResult],
        comprehension_result: Optional[ComprehensionResult],
        interaction_result: Optional[InteractionResult],
        security_result: Optional[SecurityResult],
        scoring_result: Optional[GlobalReadinessResult],
        rule_engine_result: Optional[RuleEngineResult],
        recommendation_result: Optional[RecommendationResult],
        errors: Optional[list[str]] = None,
        output_path: Optional[str] = None,
    ) -> ReportResult:
        """Render the full ARAS report for a single website.

        Every argument besides `url` and `output_path` may be `None`
        (an earlier stage did not run or failed) — the report is still
        rendered, noting whichever sections are unavailable, rather
        than raising.

        Args:
            url: The website URL that was assessed.
            evidence: The collected `WebsiteEvidence`, or `None`.
            discoverability_result: Output of `DiscoverabilityAgent`, or `None`.
            comprehension_result: Output of `ComprehensionAgent`, or `None`.
            interaction_result: Output of `InteractionAgent`, or `None`.
            security_result: Output of `SecurityAgent`, or `None`.
            scoring_result: Output of `ScoringAgent`, or `None`.
            rule_engine_result: Output of `RuleEngine`, or `None`.
            recommendation_result: Output of `RecommendationAgent`, or `None`.
            errors: Workflow-level error messages accumulated by the
                orchestrator, if any.
            output_path: Filesystem path to write the PDF to. Defaults
                to `reports/<host>_aras_report.pdf`.

        Returns:
            A `ReportResult` describing whether rendering succeeded and
            where the file was written.
        """
        resolved_path = output_path or self._default_output_path(url)

        try:
            self._ensure_parent_directory(resolved_path)
            story = self._build_story(
                url=url,
                evidence=evidence,
                discoverability_result=discoverability_result,
                comprehension_result=comprehension_result,
                interaction_result=interaction_result,
                security_result=security_result,
                scoring_result=scoring_result,
                rule_engine_result=rule_engine_result,
                recommendation_result=recommendation_result,
                errors=errors or [],
            )
            SimpleDocTemplate(resolved_path, pagesize=A4).build(story)
        except Exception as exc:  # noqa: BLE001 - report the failure, don't crash the caller
            return ReportResult(output_path=resolved_path, generated=False, error=str(exc))

        return ReportResult(output_path=resolved_path, generated=True)

    # ------------------------------------------------------------------
    # Output path resolution
    # ------------------------------------------------------------------

    @classmethod
    def _default_output_path(cls, url: str) -> str:
        """Build the default report path from a website URL.

        Args:
            url: The website URL that was assessed.

        Returns:
            `reports/<slug>_aras_report.pdf`, where `<slug>` is derived
            from the URL's hostname (e.g. `"mytek"` for
            `"https://www.mytek.tn"`).
        """
        slug = cls._slug_from_url(url)
        return str(Path(_REPORTS_DIRECTORY) / f"{slug}{_REPORT_FILENAME_SUFFIX}")

    @staticmethod
    def _slug_from_url(url: str) -> str:
        """Derive a filesystem-safe slug from a website URL's hostname.

        Args:
            url: The website URL to derive a slug from.

        Returns:
            The hostname's first label, with a leading `www.` stripped
            (e.g. `"mytek"` for `"https://www.mytek.tn"`), or `"site"`
            if no hostname could be parsed.
        """
        hostname = urlparse(url).netloc or urlparse(url).path
        hostname = hostname.split("@")[-1].split(":")[0]
        if hostname.startswith("www."):
            hostname = hostname[len("www.") :]
        return hostname.split(".")[0] or "site"

    @staticmethod
    def _ensure_parent_directory(path: str) -> None:
        """Create the report's parent directory if it does not exist yet.

        Args:
            path: The filesystem path the report will be written to.
        """
        Path(path).parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Story assembly
    # ------------------------------------------------------------------

    def _build_story(
        self,
        url: str,
        evidence: Optional[WebsiteEvidence],
        discoverability_result: Optional[DiscoverabilityResult],
        comprehension_result: Optional[ComprehensionResult],
        interaction_result: Optional[InteractionResult],
        security_result: Optional[SecurityResult],
        scoring_result: Optional[GlobalReadinessResult],
        rule_engine_result: Optional[RuleEngineResult],
        recommendation_result: Optional[RecommendationResult],
        errors: list[str],
    ) -> list[Any]:
        """Assemble the full list of ReportLab flowables for the PDF body.

        Args:
            url: The website URL that was assessed.
            evidence: The collected `WebsiteEvidence`, or `None`.
            discoverability_result: Output of `DiscoverabilityAgent`, or `None`.
            comprehension_result: Output of `ComprehensionAgent`, or `None`.
            interaction_result: Output of `InteractionAgent`, or `None`.
            security_result: Output of `SecurityAgent`, or `None`.
            scoring_result: Output of `ScoringAgent`, or `None`.
            rule_engine_result: Output of `RuleEngine`, or `None`.
            recommendation_result: Output of `RecommendationAgent`, or `None`.
            errors: Workflow-level error messages, possibly empty.

        Returns:
            The complete story to pass to `SimpleDocTemplate.build`.
        """
        styles = getSampleStyleSheet()
        heading_style = ParagraphStyle(
            "SectionHeading", parent=styles["Heading2"], spaceBefore=12, spaceAfter=6
        )
        sub_heading_style = ParagraphStyle(
            "SubHeading", parent=styles["Heading3"], spaceBefore=10, spaceAfter=4
        )

        analysis_results: dict[str, Any] = {
            "discoverability": discoverability_result,
            "comprehension": comprehension_result,
            "interaction": interaction_result,
            "security": security_result,
        }

        story: list[Any] = [
            Paragraph("ARAS Agentic Readiness Assessment Report", styles["Title"]),
            Spacer(1, 0.5 * cm),
            Paragraph(f"<b>Website:</b> {self._escape(url)}", styles["Normal"]),
        ]

        story += self._build_executive_summary_section(scoring_result, heading_style, styles)
        story += self._build_dimension_scores_section(analysis_results, heading_style, styles)
        story += self._build_evidence_section(evidence, heading_style, styles)
        story += self._build_detailed_findings_section(
            analysis_results, heading_style, sub_heading_style, styles
        )
        story += self._build_issues_section(rule_engine_result, heading_style, styles)
        story += self._build_recommendations_section(
            recommendation_result, heading_style, sub_heading_style, styles
        )
        story += self._build_errors_section(errors, heading_style, styles)

        return story

    def _build_executive_summary_section(
        self, scoring_result: Optional[GlobalReadinessResult], heading_style: Any, styles: Any
    ) -> list[Any]:
        """Build the "Executive Summary" section: global score and readiness level.

        Args:
            scoring_result: Output of `ScoringAgent`, or `None`.
            heading_style: Paragraph style for section headings.
            styles: The base ReportLab stylesheet.

        Returns:
            The flowables for this section.
        """
        section: list[Any] = [Paragraph("1. Executive Summary", heading_style)]

        if scoring_result is None:
            section.append(
                Paragraph("No global score is available for this assessment.", styles["Normal"])
            )
            return section

        readiness_level = self._readiness_level(scoring_result.global_score)
        section.append(
            Paragraph(f"<b>Global Score:</b> {scoring_result.global_score}/100", styles["Normal"])
        )
        section.append(Paragraph(f"<b>Readiness Level:</b> {readiness_level}", styles["Normal"]))
        return section

    def _build_dimension_scores_section(
        self, analysis_results: dict[str, Any], heading_style: Any, styles: Any
    ) -> list[Any]:
        """Build the "Dimension Scores" section: one row per ARAS dimension.

        Args:
            analysis_results: Mapping of dimension name to its result
                object (or `None`).
            heading_style: Paragraph style for section headings.
            styles: The base ReportLab stylesheet.

        Returns:
            The flowables for this section.
        """
        section: list[Any] = [Paragraph("2. Dimension Scores", heading_style)]

        rows = [["Dimension", "Score"]]
        for key, label in _DIMENSION_LABELS.items():
            result = analysis_results.get(key)
            score = f"{result.score}/100" if result is not None else "N/A"
            rows.append([label, score])

        table = Table(rows, colWidths=[8 * cm, 6 * cm])
        table.setStyle(self._header_table_style())
        section.append(table)
        return section

    def _build_evidence_section(
        self, evidence: Optional[WebsiteEvidence], heading_style: Any, styles: Any
    ) -> list[Any]:
        """Build the "Evidence Overview" section.

        Args:
            evidence: The collected `WebsiteEvidence`, or `None`.
            heading_style: Paragraph style for section headings.
            styles: The base ReportLab stylesheet.

        Returns:
            The flowables for this section.
        """
        section: list[Any] = [Paragraph("3. Evidence Overview", heading_style)]

        if evidence is None:
            section.append(Paragraph("Evidence collection failed; no evidence available.", styles["Normal"]))
            return section

        lines = [
            f"Status code: {evidence.status_code}",
            f"Title: {self._escape(evidence.title or '(none)')}",
            f"Collection errors: {len(evidence.errors)}",
        ]
        section.append(
            ListFlowable(
                [ListItem(Paragraph(line, styles["Normal"])) for line in lines],
                bulletType="bullet",
            )
        )
        return section

    def _build_detailed_findings_section(
        self,
        analysis_results: dict[str, Any],
        heading_style: Any,
        sub_heading_style: Any,
        styles: Any,
    ) -> list[Any]:
        """Build the "Detailed Findings" section: passed/failed checks per dimension.

        Args:
            analysis_results: Mapping of dimension name to its result
                object (or `None`).
            heading_style: Paragraph style for section headings.
            sub_heading_style: Paragraph style for per-dimension subheadings.
            styles: The base ReportLab stylesheet.

        Returns:
            The flowables for this section.
        """
        section: list[Any] = [Paragraph("4. Detailed Findings", heading_style)]

        for key, label in _DIMENSION_LABELS.items():
            result = analysis_results.get(key)
            section.append(Paragraph(label, sub_heading_style))

            if result is None:
                section.append(Paragraph("This dimension was not evaluated.", styles["Normal"]))
                continue

            passed = [name for name, ok in result.checks.items() if ok]
            failed = [name for name, ok in result.checks.items() if not ok]
            section.append(
                Paragraph(f"<b>Score:</b> {result.score}/100", styles["Normal"])
            )
            section.append(
                Paragraph(f"<b>Passed checks:</b> {self._escape(', '.join(passed) or 'none')}", styles["Normal"])
            )
            section.append(
                Paragraph(f"<b>Failed checks:</b> {self._escape(', '.join(failed) or 'none')}", styles["Normal"])
            )

        return section

    def _build_issues_section(
        self, rule_engine_result: Optional[RuleEngineResult], heading_style: Any, styles: Any
    ) -> list[Any]:
        """Build the "Classified Issues" section, grouped by priority.

        Args:
            rule_engine_result: Output of `RuleEngine`, or `None`.
            heading_style: Paragraph style for section headings.
            styles: The base ReportLab stylesheet.

        Returns:
            The flowables for this section.
        """
        section: list[Any] = [Paragraph("5. Classified Issues", heading_style)]

        if rule_engine_result is None or not rule_engine_result.issues:
            section.append(Paragraph("No issues were classified.", styles["Normal"]))
            return section

        summary = rule_engine_result.summary
        section.append(
            Paragraph(
                f"<b>HIGH:</b> {summary.get('HIGH', 0)}  "
                f"<b>MEDIUM:</b> {summary.get('MEDIUM', 0)}  "
                f"<b>LOW:</b> {summary.get('LOW', 0)}",
                styles["Normal"],
            )
        )

        rows = [["Priority", "Category", "Issue", "Criterion"]]
        for issue in sorted(
            rule_engine_result.issues, key=lambda item: _PRIORITY_ORDER.get(item.priority, 3)
        ):
            rows.append(
                [
                    issue.priority,
                    issue.category,
                    self._escape(issue.issue),
                    issue.criterion or issue.knowledge_topic,
                ]
            )

        table = Table(rows, colWidths=[2.2 * cm, 3.3 * cm, 6.5 * cm, 2.5 * cm])
        table.setStyle(self._header_table_style(font_size=8))
        section.append(table)
        return section

    def _build_recommendations_section(
        self,
        recommendation_result: Optional[RecommendationResult],
        heading_style: Any,
        sub_heading_style: Any,
        styles: Any,
    ) -> list[Any]:
        """Build the "Recommendations" section, one subsection per recommendation.

        Args:
            recommendation_result: Output of `RecommendationAgent`, or `None`.
            heading_style: Paragraph style for section headings.
            sub_heading_style: Paragraph style for per-recommendation subheadings.
            styles: The base ReportLab stylesheet.

        Returns:
            The flowables for this section.
        """
        section: list[Any] = [Paragraph("6. Recommendations", heading_style)]

        if recommendation_result is None or not recommendation_result.recommendations:
            section.append(
                Paragraph(
                    "No recommendations were generated for this assessment.", styles["Normal"]
                )
            )
            return section

        ordered = sorted(
            recommendation_result.recommendations,
            key=lambda rec: _PRIORITY_ORDER.get(rec.priority, 3),
        )
        for index, recommendation in enumerate(ordered, start=1):
            section.append(
                Paragraph(
                    f"{index}. [{recommendation.priority}] "
                    f"{self._escape(recommendation.category)} — "
                    f"{self._escape(recommendation.issue)}",
                    sub_heading_style,
                )
            )
            section.append(
                Paragraph(
                    f"<b>Explanation:</b> {self._escape(recommendation.explanation)}",
                    styles["Normal"],
                )
            )
            section.append(
                Paragraph(
                    f"<b>Recommendation:</b> {self._escape(recommendation.recommendation)}",
                    styles["Normal"],
                )
            )
            if recommendation.implementation_steps:
                section.append(Paragraph("<b>Implementation steps:</b>", styles["Normal"]))
                section.append(
                    ListFlowable(
                        [
                            ListItem(Paragraph(self._escape(step), styles["Normal"]))
                            for step in recommendation.implementation_steps
                        ],
                        bulletType="bullet",
                    )
                )
            references = (
                ", ".join(recommendation.references) if recommendation.references else "none"
            )
            section.append(
                Paragraph(f"<b>References:</b> {self._escape(references)}", styles["Normal"])
            )

        return section

    def _build_errors_section(
        self, errors: list[str], heading_style: Any, styles: Any
    ) -> list[Any]:
        """Build the "Workflow Errors" section.

        Args:
            errors: Workflow-level error messages, possibly empty.
            heading_style: Paragraph style for section headings.
            styles: The base ReportLab stylesheet.

        Returns:
            The flowables for this section.
        """
        section: list[Any] = [Paragraph("7. Workflow Errors", heading_style)]

        if not errors:
            section.append(Paragraph("No workflow errors were recorded.", styles["Normal"]))
            return section

        section.append(
            ListFlowable(
                [ListItem(Paragraph(self._escape(error), styles["Normal"])) for error in errors],
                bulletType="bullet",
            )
        )
        return section

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _header_table_style(font_size: int = 9) -> TableStyle:
        """Build the shared header-row table style used across sections.

        Args:
            font_size: Font size applied to every cell.

        Returns:
            A `TableStyle` with a dark header row and full grid lines.
        """
        return TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E3440")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("FONTSIZE", (0, 0), (-1, -1), font_size),
            ]
        )

    @staticmethod
    def _readiness_level(global_score: float) -> str:
        """Classify a global score into a human-facing readiness level.

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

    @staticmethod
    def _escape(text: str) -> str:
        """Escape text so ReportLab's mini-XML paragraph parser treats it as plain text.

        Upstream text (LLM-generated recommendations, page titles, raw
        issue messages) can contain literal angle brackets or
        ampersands, which `reportlab.platypus.Paragraph` would
        otherwise try to parse as markup and reject.

        Args:
            text: Untrusted, dynamically generated text.

        Returns:
            `text` with `&`, `<`, and `>` escaped to their XML entities.
        """
        return _xml_escape(text)

"""Comprehension Agent.

This module is the second analysis ("judgment") layer of ARAS. It
evaluates how easily an AI agent can understand the semantic
structure, meaning, and organization of a website: structured data
formats (JSON-LD, Microdata, RDFa), Schema.org entity descriptions,
metadata completeness, Open Graph social metadata, and internal
content organization.

This agent MUST NOT:
    - perform HTTP requests
    - parse HTML
    - crawl websites
    - extract structured data
    - use BeautifulSoup, HttpClient, or any extraction tool

It only reads an already-collected `WebsiteEvidence` snapshot and
turns it into a scored `ComprehensionResult`. Evidence collection
belongs to the Evidence Collector, a separate, earlier layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from models.comprehension import ComprehensionResult
from models.evidence import WebsiteEvidence

_CRITERIA_COUNT = 7
_CRITERION_WEIGHT = 100.0 / _CRITERIA_COUNT

_JSON_LD_KEY = "json-ld"
_MICRODATA_KEY = "microdata"
_RDFA_KEY = "rdfa"


@dataclass(frozen=True)
class _CriterionOutcome:
    """The result of evaluating a single comprehension criterion.

    Attributes:
        passed: Whether the criterion was satisfied.
        details: Evidence to merge into `ComprehensionResult.details`.
        issue: Message to record if the criterion failed.
        recommendation: Fix to record if the criterion failed.
    """

    passed: bool
    details: dict[str, object]
    issue: str
    recommendation: str


class ComprehensionAgent:
    """Evaluates a website's semantic comprehensibility for AI agents.

    This class holds no evidence-collection logic. It is a pure
    judgment step: it reads a `WebsiteEvidence` snapshot and scores it
    against a fixed set of equally-weighted comprehension criteria.
    """

    def evaluate(self, evidence: WebsiteEvidence) -> ComprehensionResult:
        """Evaluate comprehension from already-collected evidence.

        Args:
            evidence: The `WebsiteEvidence` snapshot to evaluate.

        Returns:
            A `ComprehensionResult` with a score in [0, 100], a
            pass/fail breakdown, supporting details, and
            recommendations for every failed criterion.
        """
        result = ComprehensionResult()

        criteria: list[tuple[str, Callable[[WebsiteEvidence], _CriterionOutcome]]] = [
            ("structured_data", self._evaluate_structured_data),
            ("json_ld", self._evaluate_json_ld),
            ("schema_entities", self._evaluate_schema_entities),
            ("metadata", self._evaluate_metadata),
            ("semantic_formats", self._evaluate_semantic_formats),
            ("open_graph", self._evaluate_open_graph),
            ("internal_structure", self._evaluate_internal_structure),
        ]

        for name, evaluator in criteria:
            self._apply(name, evaluator(evidence), result)

        result.score = self._compute_score(result.checks)
        return result

    # ------------------------------------------------------------------
    # Result assembly
    # ------------------------------------------------------------------

    @staticmethod
    def _apply(
        name: str, outcome: _CriterionOutcome, result: ComprehensionResult
    ) -> None:
        """Merge a single criterion's outcome into the aggregate result.

        Args:
            name: The criterion's key in `result.checks`.
            outcome: The evaluated outcome for this criterion.
            result: The in-progress result to update.
        """
        result.checks[name] = outcome.passed
        result.details.update(outcome.details)
        if not outcome.passed:
            result.issues.append(outcome.issue)
            result.recommendations.append(outcome.recommendation)

    @staticmethod
    def _compute_score(checks: dict[str, bool]) -> float:
        """Compute the overall score from equally-weighted criteria.

        Args:
            checks: Pass/fail outcome of every evaluated criterion.

        Returns:
            The percentage of passed criteria, in [0, 100].
        """
        if not checks:
            return 0.0
        passed = sum(1 for outcome in checks.values() if outcome)
        return round(passed * _CRITERION_WEIGHT, 2)

    # ------------------------------------------------------------------
    # Shared structured-data helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _json_ld_items(evidence: WebsiteEvidence) -> list[dict[str, Any]]:
        """Return the raw JSON-LD objects collected for this website."""
        return evidence.structured_data.get(_JSON_LD_KEY) or []

    @staticmethod
    def _microdata_items(evidence: WebsiteEvidence) -> list[dict[str, Any]]:
        """Return the raw Microdata items collected for this website."""
        return evidence.structured_data.get(_MICRODATA_KEY) or []

    @staticmethod
    def _rdfa_items(evidence: WebsiteEvidence) -> list[dict[str, Any]]:
        """Return the raw RDFa items collected for this website."""
        return evidence.structured_data.get(_RDFA_KEY) or []

    @staticmethod
    def _normalize_type(raw_type: str) -> str:
        """Reduce a raw type token to its bare Schema.org type name.

        Handles plain names (`"Product"`), CURIEs (`"schema:Product"`),
        and full URLs (`"https://schema.org/Product"`).

        Args:
            raw_type: A single raw type token.

        Returns:
            The bare type name (e.g. `"Product"`).
        """
        token = raw_type.strip()
        for separator in ("/", ":"):
            if separator in token:
                token = token.rsplit(separator, 1)[-1]
        return token

    @classmethod
    def _schema_types_from_json_ld(cls, items: list[dict[str, Any]]) -> list[str]:
        """Collect Schema.org type names declared via `@type` in JSON-LD.

        Args:
            items: The raw JSON-LD objects to inspect.

        Returns:
            A list of bare Schema.org type names, in discovery order,
            without duplicates.
        """
        types: list[str] = []
        for item in items:
            raw_type = item.get("@type")
            candidates = raw_type if isinstance(raw_type, list) else [raw_type]
            for candidate in candidates:
                if isinstance(candidate, str) and candidate.strip():
                    normalized = cls._normalize_type(candidate)
                    if normalized not in types:
                        types.append(normalized)
        return types

    # ------------------------------------------------------------------
    # 1. Structured data availability
    # ------------------------------------------------------------------

    def _evaluate_structured_data(self, evidence: WebsiteEvidence) -> _CriterionOutcome:
        """Check that at least one structured data format is present.

        Args:
            evidence: The evidence snapshot to evaluate.

        Returns:
            The outcome of this criterion.
        """
        json_ld_found = bool(self._json_ld_items(evidence))
        microdata_found = bool(self._microdata_items(evidence))
        rdfa_found = bool(self._rdfa_items(evidence))
        found = json_ld_found or microdata_found or rdfa_found

        return _CriterionOutcome(
            passed=found,
            details={
                "json_ld_found": json_ld_found,
                "microdata_found": microdata_found,
                "rdfa_found": rdfa_found,
            },
            issue="No structured data found",
            recommendation="Add JSON-LD structured data using Schema.org vocabulary.",
        )

    # ------------------------------------------------------------------
    # 2. JSON-LD semantic understanding
    # ------------------------------------------------------------------

    def _evaluate_json_ld(self, evidence: WebsiteEvidence) -> _CriterionOutcome:
        """Check that valid JSON-LD structured information exists.

        Args:
            evidence: The evidence snapshot to evaluate.

        Returns:
            The outcome of this criterion.
        """
        items = self._json_ld_items(evidence)
        found = bool(items)

        return _CriterionOutcome(
            passed=found,
            details={"json_ld_types": self._schema_types_from_json_ld(items)},
            issue="No JSON-LD semantic information found",
            recommendation="Add JSON-LD markup to describe website entities.",
        )

    # ------------------------------------------------------------------
    # 3. Schema.org entity description
    # ------------------------------------------------------------------

    def _evaluate_schema_entities(self, evidence: WebsiteEvidence) -> _CriterionOutcome:
        """Check that structured data declares explicit Schema.org types.

        Args:
            evidence: The evidence snapshot to evaluate.

        Returns:
            The outcome of this criterion.
        """
        schema_types = self._schema_types_from_json_ld(self._json_ld_items(evidence))
        found = bool(schema_types)

        return _CriterionOutcome(
            passed=found,
            details={"schema_types": schema_types},
            issue="No Schema.org entities detected",
            recommendation="Define semantic entities such as Product, Organization, Article, or FAQ.",
        )

    # ------------------------------------------------------------------
    # 4. Metadata completeness
    # ------------------------------------------------------------------

    @staticmethod
    def _evaluate_metadata(evidence: WebsiteEvidence) -> _CriterionOutcome:
        """Check that title, meta description, and language are all defined.

        Args:
            evidence: The evidence snapshot to evaluate.

        Returns:
            The outcome of this criterion.
        """
        has_title = bool(evidence.title)
        has_description = bool(evidence.meta_tags.get("description"))
        has_language = bool(evidence.language)
        passed = has_title and has_description and has_language

        details = {
            "title": evidence.title,
            "language": evidence.language,
            "has_description": has_description,
        }

        missing = [
            label
            for label, present in (
                ("title", has_title),
                ("meta description", has_description),
                ("language", has_language),
            )
            if not present
        ]
        issue = f"Missing metadata information: {', '.join(missing)}" if missing else ""
        recommendation = (
            "Add title, meta description, and language attributes."
            if missing
            else ""
        )

        return _CriterionOutcome(
            passed=passed,
            details=details,
            issue=issue,
            recommendation=recommendation,
        )

    # ------------------------------------------------------------------
    # 5. Content representation formats
    # ------------------------------------------------------------------

    def _evaluate_semantic_formats(self, evidence: WebsiteEvidence) -> _CriterionOutcome:
        """Check for multiple machine-readable semantic representations.

        Args:
            evidence: The evidence snapshot to evaluate.

        Returns:
            The outcome of this criterion.
        """
        formats_found = []
        if self._json_ld_items(evidence):
            formats_found.append(_JSON_LD_KEY)
        if self._microdata_items(evidence):
            formats_found.append(_MICRODATA_KEY)
        if self._rdfa_items(evidence):
            formats_found.append(_RDFA_KEY)

        found = bool(formats_found)

        return _CriterionOutcome(
            passed=found,
            details={"semantic_formats_found": formats_found},
            issue="Poor semantic representation",
            recommendation="Provide machine-readable content representations for AI agents.",
        )

    # ------------------------------------------------------------------
    # 6. Open Graph semantic information
    # ------------------------------------------------------------------

    @staticmethod
    def _evaluate_open_graph(evidence: WebsiteEvidence) -> _CriterionOutcome:
        """Check that at least one Open Graph tag is present.

        Args:
            evidence: The evidence snapshot to evaluate.

        Returns:
            The outcome of this criterion.
        """
        found = bool(evidence.open_graph)
        return _CriterionOutcome(
            passed=found,
            details={"open_graph_tags": list(evidence.open_graph.keys())},
            issue="Missing Open Graph metadata",
            recommendation="Add Open Graph metadata.",
        )

    # ------------------------------------------------------------------
    # 7. Internal content structure
    # ------------------------------------------------------------------

    @staticmethod
    def _evaluate_internal_structure(evidence: WebsiteEvidence) -> _CriterionOutcome:
        """Check that the website exposes navigable internal content.

        Args:
            evidence: The evidence snapshot to evaluate.

        Returns:
            The outcome of this criterion.
        """
        found = bool(evidence.internal_links)
        return _CriterionOutcome(
            passed=found,
            details={"internal_links_count": len(evidence.internal_links)},
            issue="No internal content structure found",
            recommendation="Add internal links so agents can navigate content organization.",
        )

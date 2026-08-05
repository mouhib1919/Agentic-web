"""Rule Engine.

This module is the deterministic reasoning layer of ARAS, sitting
between the Scoring Agent and the future Recommendation Agent. It
takes the raw `issues` already reported by the four analysis agents
(Discoverability, Comprehension, Interaction, Security) and turns each
one into a `ClassifiedIssue`: tagged with a deterministic priority, the
exact ARAS criterion it was evaluated against, its dimension's score,
the evidence behind it, and a `retrieval_query` ready to hand to the
RAG Retriever.

This engine MUST NOT:
    - use any LLM
    - generate natural-language recommendations
    - retrieve documents
    - access ChromaDB
    - perform website analysis
    - modify any analysis agent's score
    - recalculate any score
    - change priority classification logic

It only reads the `issues`/`checks`/`score` already produced by the
analysis agents and classifies them via fixed, inspectable rule
tables — no model call, no randomness, no external I/O. The rule
tables' `keywords`/`priority`/`reason` ordering and values are
unchanged from the original implementation; only a `criterion` key was
added to each rule, mapping it to the exact ARAS criterion name (as
used by the analysis agents' own `checks` dict and the
`knowledge/aras_knowledge/` frontmatter) for RAG retrieval purposes.
"""

from __future__ import annotations

from typing import Any, Optional

from models.rule_engine import ClassifiedIssue, RuleEngineResult

_PRIORITY_LEVELS = ("HIGH", "MEDIUM", "LOW")
_DEFAULT_PRIORITY = "MEDIUM"

# ---------------------------------------------------------------------------
# Rule tables
#
# Each rule is matched against an issue message by checking whether every
# keyword in `keywords` appears in the message (case-insensitive, with
# hyphens normalized to spaces so "Content-Security-Policy" and "Content
# Security Policy" match the same rule). Rules are checked in order and the
# first match wins, so more specific rules should be listed before broader
# ones. An issue that matches no rule in its category falls back to the
# category's default entry, keeping the engine total: every issue always
# receives a classification.
# ---------------------------------------------------------------------------

_SECURITY_RULES: list[dict[str, Any]] = [
    {
        "keywords": ("content security policy",),
        "priority": "HIGH",
        "topic": "csp",
        "criterion": "csp",
        "reason": "Missing CSP leaves the site open to script injection and XSS attacks.",
    },
    {
        "keywords": ("hsts",),
        "priority": "HIGH",
        "topic": "hsts",
        "criterion": "hsts",
        "reason": "Missing HSTS allows connections to be silently downgraded to plaintext HTTP.",
    },
    {
        "keywords": ("x frame options",),
        "priority": "HIGH",
        "topic": "security_headers",
        "criterion": "x_frame_options",
        "reason": "Missing clickjacking protection is a high-impact, low-effort security gap.",
    },
    {
        "keywords": ("mime",),
        "priority": "HIGH",
        "topic": "security_headers",
        "criterion": "mime_xss",
        "reason": "Missing MIME/XSS protection headers is a high-impact, low-effort security gap.",
    },
    {
        "keywords": ("https is not enabled",),
        "priority": "MEDIUM",
        "topic": "hsts",
        "criterion": "https",
        "reason": "Serving traffic over plain HTTP is a weak security configuration.",
    },
    {
        "keywords": ("reverse proxy",),
        "priority": "MEDIUM",
        "topic": "security_headers",
        "criterion": "infrastructure_security",
        "reason": "No recognized CDN/WAF is a weak security configuration, not a missing control.",
    },
    {
        "keywords": ("http 200",),
        "priority": "MEDIUM",
        "topic": "security_headers",
        "criterion": "http_status",
        "reason": "An unavailable homepage is a weak, informational security configuration signal.",
    },
]
_SECURITY_DEFAULT_TOPIC = "security_headers"
_SECURITY_DEFAULT_CRITERION = "infrastructure_security"

_INTERACTION_RULES: list[dict[str, Any]] = [
    {
        "keywords": ("api interaction surface",),
        "priority": "HIGH",
        "topic": "openapi",
        "criterion": "api_availability",
        "reason": "No executable API surface blocks direct agent interaction entirely.",
    },
    {
        "keywords": ("backend api endpoints",),
        "priority": "HIGH",
        "topic": "openapi",
        "criterion": "api_availability",
        "reason": "No backend API endpoints blocks direct agent interaction entirely.",
    },
    {
        "keywords": ("graphql",),
        "priority": "MEDIUM",
        "topic": "graphql",
        "criterion": "graphql",
        "reason": "Missing GraphQL documentation limits flexible, relationship-aware agent queries.",
    },
    {
        "keywords": ("api documentation",),
        "priority": "MEDIUM",
        "topic": "openapi",
        "criterion": "api_documentation",
        "reason": "Missing API documentation prevents agents from learning how to call the API.",
    },
    {
        "keywords": ("mcp endpoint",),
        "priority": "MEDIUM",
        "topic": "openapi",
        "criterion": "mcp_endpoint",
        "reason": "Missing MCP support limits agent-native interaction capabilities.",
    },
    {
        "keywords": ("mcp tools",),
        "priority": "MEDIUM",
        "topic": "openapi",
        "criterion": "mcp_tools",
        "reason": "Missing MCP support limits agent-native interaction capabilities.",
    },
    {
        "keywords": ("frontend interaction",),
        "priority": "LOW",
        "topic": "openapi",
        "criterion": "frontend_interaction",
        "reason": "Limited frontend interaction is a minor, fallback-only readiness gap.",
    },
]
_INTERACTION_DEFAULT_TOPIC = "openapi"
_INTERACTION_DEFAULT_CRITERION = "api_documentation"

_COMPREHENSION_RULES: list[dict[str, Any]] = [
    {
        "keywords": ("json ld",),
        "priority": "MEDIUM",
        "topic": "jsonld",
        "criterion": "json_ld",
        "reason": "Missing JSON-LD prevents agents from reliably extracting page semantics.",
    },
    {
        "keywords": ("schema.org",),
        "priority": "MEDIUM",
        "topic": "schemaorg",
        "criterion": "schema_entities",
        "reason": "Missing Schema.org entities leaves page content ambiguous to parse.",
    },
    {
        "keywords": ("schema entities",),
        "priority": "MEDIUM",
        "topic": "schemaorg",
        "criterion": "schema_entities",
        "reason": "Missing Schema.org entities leaves page content ambiguous to parse.",
    },
    {
        "keywords": ("structured data",),
        "priority": "MEDIUM",
        "topic": "jsonld",
        "criterion": "structured_data",
        "reason": "No structured data at all removes the primary machine-readable content signal.",
    },
    {
        "keywords": ("open graph",),
        "priority": "LOW",
        "topic": "schemaorg",
        "criterion": "open_graph",
        "reason": "Missing Open Graph metadata is a minor social/metadata readiness gap.",
    },
    {
        "keywords": ("semantic representation",),
        "priority": "LOW",
        "topic": "jsonld",
        "criterion": "semantic_formats",
        "reason": "Weak semantic representation is a lower-impact comprehension gap.",
    },
    {
        "keywords": ("missing metadata information",),
        "priority": "MEDIUM",
        "topic": "metadata",
        "criterion": "metadata",
        "reason": "Missing title, description, or language metadata limits how well agents can comprehend the page.",
    },
    {
        "keywords": ("internal content structure",),
        "priority": "MEDIUM",
        "topic": "internal_structure",
        "criterion": "internal_structure",
        "reason": "Poor internal content structure makes the page harder for agents to comprehend and segment.",
    },
]
_COMPREHENSION_DEFAULT_TOPIC = "schemaorg"
_COMPREHENSION_DEFAULT_CRITERION = "structured_data"

_DISCOVERABILITY_RULES: list[dict[str, Any]] = [
    {
        "keywords": ("sitemap",),
        "priority": "MEDIUM",
        "topic": "sitemap",
        "criterion": "sitemap",
        "reason": "Missing sitemap.xml slows down content discovery for crawlers and agents.",
    },
    {
        "keywords": ("robots.txt",),
        "priority": "MEDIUM",
        "topic": "robots",
        "criterion": "robots_txt",
        "reason": "Missing robots.txt removes the first discovery signal an agent looks for.",
    },
    {
        "keywords": ("llms.txt",),
        "priority": "LOW",
        "topic": "llms",
        "criterion": "llms_txt",
        "reason": "Missing llms.txt is a minor, emerging-convention discoverability gap.",
    },
    {
        "keywords": ("open graph",),
        "priority": "MEDIUM",
        "topic": "open_graph",
        "criterion": "open_graph",
        "reason": "Missing Open Graph metadata limits how well agents can identify and summarize the page.",
    },
    {
        "keywords": ("api documentation found",),
        "priority": "MEDIUM",
        "topic": "api_discoverability",
        "criterion": "api_discoverability",
        "reason": "No discoverable API surface prevents agents from finding a programmatic entry point.",
    },
    {
        "keywords": ("internal navigation links",),
        "priority": "MEDIUM",
        "topic": "internal_links",
        "criterion": "internal_links",
        "reason": "No internal navigation links limits how much of the site agents can discover from the homepage.",
    },
    {
        "keywords": ("missing metadata:",),
        "priority": "MEDIUM",
        "topic": "metadata",
        "criterion": "metadata",
        "reason": "Missing title, description, or canonical metadata weakens the page's basic discoverability signals.",
    },
]
_DISCOVERABILITY_DEFAULT_TOPIC = "sitemap"
_DISCOVERABILITY_DEFAULT_CRITERION = "sitemap"


class RuleEngine:
    """Classifies analysis-agent issues into prioritized, topic-tagged entries.

    This class holds no LLM, retrieval, or evidence-analysis logic. It
    is a pure, deterministic transformation step: `issues` lists from
    the four analysis results in, `ClassifiedIssue` list + summary out.
    """

    def evaluate(self, analysis_results: dict[str, Optional[Any]]) -> RuleEngineResult:
        """Classify every issue reported across all four analysis dimensions.

        Args:
            analysis_results: A mapping with keys `"discoverability"`,
                `"comprehension"`, `"interaction"`, and `"security"`,
                each holding the corresponding analysis result object
                (`DiscoverabilityResult`, `ComprehensionResult`,
                `InteractionResult`, `SecurityResult`) or `None` if
                that dimension was not evaluated. Each result's
                `issues` attribute drives which issues are classified;
                `score` and `checks` (both read defensively via
                `getattr`, so a minimal stand-in exposing only `issues`
                still works) are carried over unchanged into
                `ClassifiedIssue.score`/`.evidence` — never recalculated.

        Returns:
            A `RuleEngineResult` containing every classified issue and
            a priority-level summary count.
        """
        classified_issues: list[ClassifiedIssue] = []
        classified_issues += self._evaluate_discoverability_rules(
            analysis_results.get("discoverability")
        )
        classified_issues += self._evaluate_comprehension_rules(
            analysis_results.get("comprehension")
        )
        classified_issues += self._evaluate_interaction_rules(
            analysis_results.get("interaction")
        )
        classified_issues += self._evaluate_security_rules(
            analysis_results.get("security")
        )

        return RuleEngineResult(
            issues=classified_issues,
            summary=self._summarize(classified_issues),
        )

    # ------------------------------------------------------------------
    # Input access
    # ------------------------------------------------------------------

    @staticmethod
    def _issues_of(result: Optional[Any]) -> list[str]:
        """Read an analysis result's issues, defaulting to empty if absent.

        Args:
            result: An analysis result object, or `None`.

        Returns:
            The result's `issues` list, or `[]` if `result` is `None`.
        """
        return result.issues if result is not None else []

    @staticmethod
    def _score_of(result: Optional[Any]) -> float:
        """Read a dimension result's already-computed score.

        Args:
            result: An analysis result object, or `None`.

        Returns:
            The result's `score`, or `0.0` if `result` is `None` or
            exposes no `score` attribute (e.g. a minimal test stand-in).
        """
        return getattr(result, "score", 0.0) or 0.0

    @staticmethod
    def _checks_of(result: Optional[Any]) -> dict[str, bool]:
        """Read a dimension result's per-criterion pass/fail outcomes.

        Args:
            result: An analysis result object, or `None`.

        Returns:
            The result's `checks` mapping, or `{}` if `result` is
            `None` or exposes no `checks` attribute.
        """
        return getattr(result, "checks", {}) or {}

    # ------------------------------------------------------------------
    # Per-category rule evaluation
    # ------------------------------------------------------------------

    def _evaluate_security_rules(self, result: Optional[Any]) -> list[ClassifiedIssue]:
        """Classify every security-dimension issue.

        Args:
            result: `SecurityAgent`'s output, or `None`.

        Returns:
            One `ClassifiedIssue` per issue reported by `result`.
        """
        return [
            self._classify(
                issue, "security", _SECURITY_RULES, _SECURITY_DEFAULT_TOPIC,
                _SECURITY_DEFAULT_CRITERION, result,
            )
            for issue in self._issues_of(result)
        ]

    def _evaluate_interaction_rules(self, result: Optional[Any]) -> list[ClassifiedIssue]:
        """Classify every interaction-dimension issue.

        Args:
            result: `InteractionAgent`'s output, or `None`.

        Returns:
            One `ClassifiedIssue` per issue reported by `result`.
        """
        return [
            self._classify(
                issue, "interaction", _INTERACTION_RULES, _INTERACTION_DEFAULT_TOPIC,
                _INTERACTION_DEFAULT_CRITERION, result,
            )
            for issue in self._issues_of(result)
        ]

    def _evaluate_comprehension_rules(self, result: Optional[Any]) -> list[ClassifiedIssue]:
        """Classify every comprehension-dimension issue.

        Args:
            result: `ComprehensionAgent`'s output, or `None`.

        Returns:
            One `ClassifiedIssue` per issue reported by `result`.
        """
        return [
            self._classify(
                issue, "comprehension", _COMPREHENSION_RULES, _COMPREHENSION_DEFAULT_TOPIC,
                _COMPREHENSION_DEFAULT_CRITERION, result,
            )
            for issue in self._issues_of(result)
        ]

    def _evaluate_discoverability_rules(self, result: Optional[Any]) -> list[ClassifiedIssue]:
        """Classify every discoverability-dimension issue.

        Args:
            result: `DiscoverabilityAgent`'s output, or `None`.

        Returns:
            One `ClassifiedIssue` per issue reported by `result`.
        """
        return [
            self._classify(
                issue, "discoverability", _DISCOVERABILITY_RULES, _DISCOVERABILITY_DEFAULT_TOPIC,
                _DISCOVERABILITY_DEFAULT_CRITERION, result,
            )
            for issue in self._issues_of(result)
        ]

    # ------------------------------------------------------------------
    # Shared matching logic
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize(text: str) -> str:
        """Normalize an issue message for keyword matching.

        Lowercases the text and replaces hyphens with spaces, so
        equivalent phrasing (`"Content-Security-Policy"` vs `"Content
        Security Policy"`) matches the same rule regardless of which
        agent produced the message or how the task's own examples
        phrase it.

        Args:
            text: The raw issue message.

        Returns:
            The normalized message, used only for matching (the
            original, unmodified message is still stored on the
            resulting `ClassifiedIssue`).
        """
        return text.lower().replace("-", " ")

    def _classify(
        self,
        issue: str,
        category: str,
        rules: list[dict[str, Any]],
        default_topic: str,
        default_criterion: str,
        result: Optional[Any],
    ) -> ClassifiedIssue:
        """Classify a single issue against a category's rule table.

        Rules are tried in order; the first rule whose every keyword
        appears in the normalized issue message wins. If no rule
        matches, the issue still receives a classification via the
        category's default priority, topic, and criterion, so every
        issue is always represented in the output. This matching logic
        (keywords, order, priority, reason) is unchanged from before —
        only the RAG-oriented fields built in `_enrich` are new.

        Args:
            issue: The raw issue message to classify.
            category: The ARAS dimension this issue belongs to.
            rules: The category's ordered rule table.
            default_topic: The legacy knowledge topic to fall back to
                when no rule matches.
            default_criterion: The ARAS criterion to fall back to when
                no rule matches.
            result: The category's analysis result (for `score`/
                `checks`), or `None`.

        Returns:
            The resulting `ClassifiedIssue`.
        """
        normalized_issue = self._normalize(issue)
        for rule in rules:
            if all(keyword in normalized_issue for keyword in rule["keywords"]):
                return self._enrich(
                    category=category,
                    issue=issue,
                    priority=rule["priority"],
                    topic=rule["topic"],
                    criterion=rule["criterion"],
                    reason=rule["reason"],
                    result=result,
                )

        return self._enrich(
            category=category,
            issue=issue,
            priority=_DEFAULT_PRIORITY,
            topic=default_topic,
            criterion=default_criterion,
            reason=f"No specific rule matched; treated as a general {category} improvement.",
            result=result,
        )

    def _enrich(
        self,
        category: str,
        issue: str,
        priority: str,
        topic: str,
        criterion: str,
        reason: str,
        result: Optional[Any],
    ) -> ClassifiedIssue:
        """Build a fully-populated `ClassifiedIssue`, RAG fields included.

        Args:
            category: The ARAS dimension this issue belongs to.
            issue: The raw issue message.
            priority: The issue's deterministic priority.
            topic: The legacy `knowledge_topic` value (unchanged).
            criterion: The exact ARAS criterion this issue maps to.
            reason: The priority's justification.
            result: The category's analysis result (for `score`/
                `checks`), or `None`.

        Returns:
            The resulting `ClassifiedIssue`, with `score` carried over
            from `result.score` (never recalculated) and `evidence`
            populated from `result.checks[criterion]` when available.
        """
        checks = self._checks_of(result)
        evidence = {criterion: checks[criterion]} if criterion in checks else {}

        return ClassifiedIssue(
            category=category,
            issue=issue,
            priority=priority,
            knowledge_topic=topic,
            reason=reason,
            criterion=criterion,
            score=self._score_of(result),
            evidence=evidence,
            retrieval_query={"category": category, "criterion": criterion},
        )

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    @staticmethod
    def _summarize(classified_issues: list[ClassifiedIssue]) -> dict[str, int]:
        """Count classified issues per priority level.

        Args:
            classified_issues: Every issue classified by `evaluate`.

        Returns:
            A dict with `"HIGH"`, `"MEDIUM"`, and `"LOW"` keys, always
            present (even at 0), mapped to their respective counts.
        """
        summary = {priority: 0 for priority in _PRIORITY_LEVELS}
        for classified_issue in classified_issues:
            summary[classified_issue.priority] = summary.get(classified_issue.priority, 0) + 1
        return summary

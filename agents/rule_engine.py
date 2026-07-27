"""Rule Engine.

This module is the deterministic reasoning layer of ARAS, sitting
between the Scoring Agent and the future Recommendation Agent. It
takes the raw `issues` already reported by the four analysis agents
(Discoverability, Comprehension, Interaction, Security) and turns each
one into a `ClassifiedIssue`: tagged with a deterministic priority and
the knowledge-base topic the RAG Retriever should later search for.

This engine MUST NOT:
    - use any LLM
    - generate natural-language recommendations
    - retrieve documents
    - access ChromaDB
    - perform website analysis
    - modify any analysis agent's score

It only reads the `issues` lists already produced by the analysis
agents and classifies them via fixed, inspectable rule tables — no
model call, no randomness, no external I/O.
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
        "reason": "Missing CSP leaves the site open to script injection and XSS attacks.",
    },
    {
        "keywords": ("hsts",),
        "priority": "HIGH",
        "topic": "hsts",
        "reason": "Missing HSTS allows connections to be silently downgraded to plaintext HTTP.",
    },
    {
        "keywords": ("x frame options",),
        "priority": "HIGH",
        "topic": "security_headers",
        "reason": "Missing clickjacking protection is a high-impact, low-effort security gap.",
    },
    {
        "keywords": ("mime",),
        "priority": "HIGH",
        "topic": "security_headers",
        "reason": "Missing MIME/XSS protection headers is a high-impact, low-effort security gap.",
    },
    {
        "keywords": ("https is not enabled",),
        "priority": "MEDIUM",
        "topic": "hsts",
        "reason": "Serving traffic over plain HTTP is a weak security configuration.",
    },
    {
        "keywords": ("reverse proxy",),
        "priority": "MEDIUM",
        "topic": "security_headers",
        "reason": "No recognized CDN/WAF is a weak security configuration, not a missing control.",
    },
    {
        "keywords": ("http 200",),
        "priority": "MEDIUM",
        "topic": "security_headers",
        "reason": "An unavailable homepage is a weak, informational security configuration signal.",
    },
]
_SECURITY_DEFAULT_TOPIC = "security_headers"

_INTERACTION_RULES: list[dict[str, Any]] = [
    {
        "keywords": ("api interaction surface",),
        "priority": "HIGH",
        "topic": "openapi",
        "reason": "No executable API surface blocks direct agent interaction entirely.",
    },
    {
        "keywords": ("backend api endpoints",),
        "priority": "HIGH",
        "topic": "openapi",
        "reason": "No backend API endpoints blocks direct agent interaction entirely.",
    },
    {
        "keywords": ("graphql",),
        "priority": "MEDIUM",
        "topic": "graphql",
        "reason": "Missing GraphQL documentation limits flexible, relationship-aware agent queries.",
    },
    {
        "keywords": ("api documentation",),
        "priority": "MEDIUM",
        "topic": "openapi",
        "reason": "Missing API documentation prevents agents from learning how to call the API.",
    },
    {
        "keywords": ("mcp",),
        "priority": "MEDIUM",
        "topic": "openapi",
        "reason": "Missing MCP support limits agent-native interaction capabilities.",
    },
    {
        "keywords": ("frontend interaction",),
        "priority": "LOW",
        "topic": "openapi",
        "reason": "Limited frontend interaction is a minor, fallback-only readiness gap.",
    },
]
_INTERACTION_DEFAULT_TOPIC = "openapi"

_COMPREHENSION_RULES: list[dict[str, Any]] = [
    {
        "keywords": ("json ld",),
        "priority": "MEDIUM",
        "topic": "jsonld",
        "reason": "Missing JSON-LD prevents agents from reliably extracting page semantics.",
    },
    {
        "keywords": ("schema.org",),
        "priority": "MEDIUM",
        "topic": "schemaorg",
        "reason": "Missing Schema.org entities leaves page content ambiguous to parse.",
    },
    {
        "keywords": ("schema entities",),
        "priority": "MEDIUM",
        "topic": "schemaorg",
        "reason": "Missing Schema.org entities leaves page content ambiguous to parse.",
    },
    {
        "keywords": ("structured data",),
        "priority": "MEDIUM",
        "topic": "jsonld",
        "reason": "No structured data at all removes the primary machine-readable content signal.",
    },
    {
        "keywords": ("open graph",),
        "priority": "LOW",
        "topic": "schemaorg",
        "reason": "Missing Open Graph metadata is a minor social/metadata readiness gap.",
    },
    {
        "keywords": ("semantic representation",),
        "priority": "LOW",
        "topic": "jsonld",
        "reason": "Weak semantic representation is a lower-impact comprehension gap.",
    },
]
_COMPREHENSION_DEFAULT_TOPIC = "schemaorg"

_DISCOVERABILITY_RULES: list[dict[str, Any]] = [
    {
        "keywords": ("sitemap",),
        "priority": "MEDIUM",
        "topic": "sitemap",
        "reason": "Missing sitemap.xml slows down content discovery for crawlers and agents.",
    },
    {
        "keywords": ("robots.txt",),
        "priority": "MEDIUM",
        "topic": "robots",
        "reason": "Missing robots.txt removes the first discovery signal an agent looks for.",
    },
    {
        "keywords": ("llms.txt",),
        "priority": "LOW",
        "topic": "llms",
        "reason": "Missing llms.txt is a minor, emerging-convention discoverability gap.",
    },
]
_DISCOVERABILITY_DEFAULT_TOPIC = "sitemap"


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
                that dimension was not evaluated. Only each result's
                `issues` attribute is read.

        Returns:
            A `RuleEngineResult` containing every classified issue and
            a priority-level summary count.
        """
        classified_issues: list[ClassifiedIssue] = []
        classified_issues += self._evaluate_discoverability_rules(
            self._issues_of(analysis_results.get("discoverability"))
        )
        classified_issues += self._evaluate_comprehension_rules(
            self._issues_of(analysis_results.get("comprehension"))
        )
        classified_issues += self._evaluate_interaction_rules(
            self._issues_of(analysis_results.get("interaction"))
        )
        classified_issues += self._evaluate_security_rules(
            self._issues_of(analysis_results.get("security"))
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

    # ------------------------------------------------------------------
    # Per-category rule evaluation
    # ------------------------------------------------------------------

    def _evaluate_security_rules(self, issues: list[str]) -> list[ClassifiedIssue]:
        """Classify every security-dimension issue.

        Args:
            issues: Issue messages reported by `SecurityAgent`.

        Returns:
            One `ClassifiedIssue` per input issue.
        """
        return [
            self._classify(issue, "security", _SECURITY_RULES, _SECURITY_DEFAULT_TOPIC)
            for issue in issues
        ]

    def _evaluate_interaction_rules(self, issues: list[str]) -> list[ClassifiedIssue]:
        """Classify every interaction-dimension issue.

        Args:
            issues: Issue messages reported by `InteractionAgent`.

        Returns:
            One `ClassifiedIssue` per input issue.
        """
        return [
            self._classify(issue, "interaction", _INTERACTION_RULES, _INTERACTION_DEFAULT_TOPIC)
            for issue in issues
        ]

    def _evaluate_comprehension_rules(self, issues: list[str]) -> list[ClassifiedIssue]:
        """Classify every comprehension-dimension issue.

        Args:
            issues: Issue messages reported by `ComprehensionAgent`.

        Returns:
            One `ClassifiedIssue` per input issue.
        """
        return [
            self._classify(
                issue, "comprehension", _COMPREHENSION_RULES, _COMPREHENSION_DEFAULT_TOPIC
            )
            for issue in issues
        ]

    def _evaluate_discoverability_rules(self, issues: list[str]) -> list[ClassifiedIssue]:
        """Classify every discoverability-dimension issue.

        Args:
            issues: Issue messages reported by `DiscoverabilityAgent`.

        Returns:
            One `ClassifiedIssue` per input issue.
        """
        return [
            self._classify(
                issue, "discoverability", _DISCOVERABILITY_RULES, _DISCOVERABILITY_DEFAULT_TOPIC
            )
            for issue in issues
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
    ) -> ClassifiedIssue:
        """Classify a single issue against a category's rule table.

        Rules are tried in order; the first rule whose every keyword
        appears in the normalized issue message wins. If no rule
        matches, the issue still receives a classification via the
        category's default priority and topic, so every issue is
        always represented in the output.

        Args:
            issue: The raw issue message to classify.
            category: The ARAS dimension this issue belongs to.
            rules: The category's ordered rule table.
            default_topic: The knowledge topic to fall back to when no
                rule matches.

        Returns:
            The resulting `ClassifiedIssue`.
        """
        normalized_issue = self._normalize(issue)
        for rule in rules:
            if all(keyword in normalized_issue for keyword in rule["keywords"]):
                return ClassifiedIssue(
                    category=category,
                    issue=issue,
                    priority=rule["priority"],
                    knowledge_topic=rule["topic"],
                    reason=rule["reason"],
                )

        return ClassifiedIssue(
            category=category,
            issue=issue,
            priority=_DEFAULT_PRIORITY,
            knowledge_topic=default_topic,
            reason=f"No specific rule matched; treated as a general {category} improvement.",
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

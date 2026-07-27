"""Unit tests for :class:`RuleEngine`.

Rather than random synthetic scenarios, the primary test reproduces
the actual issues reported by the four analysis agents against
`https://www.mytek.tn` (see `tests/test_orchestrator.py` and
`tests/test_scoring_agent.py` for the full real-site runs these issue
messages were taken from). Additional tests cover priority-rule edge
cases and the summary aggregation in isolation.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

# Allow running this file directly (e.g. from an IDE "Run" button) by
# ensuring the project root is importable, not just the `tests/` folder.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.rule_engine import RuleEngine
from models.rule_engine import ClassifiedIssue, RuleEngineResult


@dataclass
class _FakeAnalysisResult:
    """Minimal stand-in for a *Result dataclass, exposing only `issues`.

    The Rule Engine only ever reads `.issues` off an analysis result,
    so a lightweight fake keeps these tests focused on rule-engine
    behavior rather than depending on constructing full
    DiscoverabilityResult/ComprehensionResult/InteractionResult/
    SecurityResult objects.
    """

    issues: list[str] = field(default_factory=list)


def _print_classified_issues(label: str, result: RuleEngineResult) -> None:
    print(f"--- {label} ---")
    print("Detected issues:")
    for index, classified in enumerate(result.issues, start=1):
        print(f"{index}.")
        print(f"  Category: {classified.category}")
        print(f"  Issue: {classified.issue}")
        print(f"  Priority: {classified.priority}")
        print(f"  Knowledge topic: {classified.knowledge_topic}")
        print(f"  Reason: {classified.reason}")
    print(f"Summary: {result.summary}")
    print()


def _mytek_analysis_results() -> dict[str, _FakeAnalysisResult]:
    """Reproduce the real analysis-agent issues observed for mytek.tn.

    Security and comprehension issue text is taken verbatim from the
    real `SecurityAgent`/`ComprehensionAgent` output against
    `https://www.mytek.tn`. Interaction and discoverability issue text
    matches the task's own worked example; both phrasings are covered
    because `RuleEngine` matches on normalized keywords, not exact
    strings.
    """
    return {
        "security": _FakeAnalysisResult(issues=["Missing Content-Security-Policy header."]),
        "comprehension": _FakeAnalysisResult(
            issues=["No JSON-LD semantic information found"]
        ),
        "interaction": _FakeAnalysisResult(issues=["No backend API endpoints detected"]),
        "discoverability": _FakeAnalysisResult(issues=["No llms.txt found"]),
    }


def test_mytek_analysis_results_are_classified_correctly() -> None:
    """The exact mytek-derived issue set maps to the expected classification."""
    engine = RuleEngine()

    result = engine.evaluate(_mytek_analysis_results())
    _print_classified_issues("mytek analysis results", result)

    assert len(result.issues) == 4
    by_category = {issue.category: issue for issue in result.issues}

    security_issue = by_category["security"]
    assert security_issue.issue == "Missing Content-Security-Policy header."
    assert security_issue.priority == "HIGH"
    assert security_issue.knowledge_topic == "csp"

    comprehension_issue = by_category["comprehension"]
    assert comprehension_issue.issue == "No JSON-LD semantic information found"
    assert comprehension_issue.priority == "MEDIUM"
    assert comprehension_issue.knowledge_topic == "jsonld"

    interaction_issue = by_category["interaction"]
    assert interaction_issue.issue == "No backend API endpoints detected"
    assert interaction_issue.priority == "HIGH"
    assert interaction_issue.knowledge_topic == "openapi"

    discoverability_issue = by_category["discoverability"]
    assert discoverability_issue.issue == "No llms.txt found"
    assert discoverability_issue.priority == "LOW"
    assert discoverability_issue.knowledge_topic == "llms"

    assert result.summary == {"HIGH": 2, "MEDIUM": 1, "LOW": 1}


def test_security_rules_cover_csp_hsts_and_headers() -> None:
    """Security priority rules: CSP/HSTS/security headers all classify HIGH."""
    engine = RuleEngine()
    analysis_results = {
        "security": _FakeAnalysisResult(
            issues=[
                "Missing Content-Security-Policy header.",
                "No HSTS header detected.",
                "Missing X-Frame-Options header.",
                "Missing MIME/XSS protection headers.",
            ]
        )
    }

    result = engine.evaluate(analysis_results)
    _print_classified_issues("security header rules", result)

    assert all(issue.priority == "HIGH" for issue in result.issues)
    topics = {issue.knowledge_topic for issue in result.issues}
    assert topics == {"csp", "hsts", "security_headers"}


def test_interaction_rules_distinguish_missing_surface_from_missing_docs() -> None:
    """No API surface at all is HIGH; missing docs for an existing API is MEDIUM."""
    engine = RuleEngine()
    analysis_results = {
        "interaction": _FakeAnalysisResult(
            issues=[
                "No executable API interaction surface detected.",
                "No API documentation available.",
                "No GraphQL endpoint detected.",
                "No actionable frontend interaction detected.",
            ]
        )
    }

    result = engine.evaluate(analysis_results)
    _print_classified_issues("interaction rules", result)

    by_issue = {issue.issue: issue for issue in result.issues}
    assert by_issue["No executable API interaction surface detected."].priority == "HIGH"
    assert by_issue["No API documentation available."].priority == "MEDIUM"
    assert by_issue["No API documentation available."].knowledge_topic == "openapi"
    assert by_issue["No GraphQL endpoint detected."].priority == "MEDIUM"
    assert by_issue["No GraphQL endpoint detected."].knowledge_topic == "graphql"
    assert by_issue["No actionable frontend interaction detected."].priority == "LOW"


def test_comprehension_rules_cover_jsonld_schema_and_open_graph() -> None:
    """Comprehension rules: JSON-LD/Schema.org are MEDIUM, Open Graph is LOW."""
    engine = RuleEngine()
    analysis_results = {
        "comprehension": _FakeAnalysisResult(
            issues=[
                "No JSON-LD semantic information found",
                "No Schema.org entities detected",
                "Missing Open Graph metadata",
            ]
        )
    }

    result = engine.evaluate(analysis_results)
    _print_classified_issues("comprehension rules", result)

    by_issue = {issue.issue: issue for issue in result.issues}
    assert by_issue["No JSON-LD semantic information found"].priority == "MEDIUM"
    assert by_issue["No JSON-LD semantic information found"].knowledge_topic == "jsonld"
    assert by_issue["No Schema.org entities detected"].priority == "MEDIUM"
    assert by_issue["No Schema.org entities detected"].knowledge_topic == "schemaorg"
    assert by_issue["Missing Open Graph metadata"].priority == "LOW"


def test_discoverability_rules_cover_sitemap_robots_and_llms() -> None:
    """Discoverability rules: sitemap/robots are MEDIUM, llms.txt is LOW."""
    engine = RuleEngine()
    analysis_results = {
        "discoverability": _FakeAnalysisResult(
            issues=[
                "No sitemap.xml found",
                "No robots.txt found",
                "No llms.txt found",
            ]
        )
    }

    result = engine.evaluate(analysis_results)
    _print_classified_issues("discoverability rules", result)

    by_issue = {issue.issue: issue for issue in result.issues}
    assert by_issue["No sitemap.xml found"].priority == "MEDIUM"
    assert by_issue["No sitemap.xml found"].knowledge_topic == "sitemap"
    assert by_issue["No robots.txt found"].priority == "MEDIUM"
    assert by_issue["No robots.txt found"].knowledge_topic == "robots"
    assert by_issue["No llms.txt found"].priority == "LOW"
    assert by_issue["No llms.txt found"].knowledge_topic == "llms"


def test_unmatched_issue_falls_back_to_category_default() -> None:
    """An issue matching no specific rule still gets a full classification."""
    engine = RuleEngine()
    analysis_results = {
        "security": _FakeAnalysisResult(issues=["Some entirely novel security concern"]),
    }

    result = engine.evaluate(analysis_results)
    _print_classified_issues("unmatched issue fallback", result)

    assert len(result.issues) == 1
    fallback_issue = result.issues[0]
    assert fallback_issue.priority == "MEDIUM"
    assert fallback_issue.knowledge_topic == "security_headers"
    assert isinstance(fallback_issue, ClassifiedIssue)


def test_missing_dimension_results_do_not_break_evaluation() -> None:
    """Dimensions with a `None` result contribute no issues, without erroring."""
    engine = RuleEngine()
    analysis_results = {
        "security": _FakeAnalysisResult(issues=["Missing Content-Security-Policy header."]),
        "comprehension": None,
        "interaction": None,
        "discoverability": None,
    }

    result = engine.evaluate(analysis_results)
    _print_classified_issues("missing dimensions", result)

    assert len(result.issues) == 1
    assert result.summary == {"HIGH": 1, "MEDIUM": 0, "LOW": 0}


def test_no_issues_produces_empty_result() -> None:
    """A perfectly clean site produces no classified issues at all."""
    engine = RuleEngine()

    result = engine.evaluate(
        {
            "security": _FakeAnalysisResult(issues=[]),
            "comprehension": _FakeAnalysisResult(issues=[]),
            "interaction": _FakeAnalysisResult(issues=[]),
            "discoverability": _FakeAnalysisResult(issues=[]),
        }
    )
    _print_classified_issues("no issues", result)

    assert result.issues == []
    assert result.summary == {"HIGH": 0, "MEDIUM": 0, "LOW": 0}


if __name__ == "__main__":
    test_mytek_analysis_results_are_classified_correctly()
    test_security_rules_cover_csp_hsts_and_headers()
    test_interaction_rules_distinguish_missing_surface_from_missing_docs()
    test_comprehension_rules_cover_jsonld_schema_and_open_graph()
    test_discoverability_rules_cover_sitemap_robots_and_llms()
    test_unmatched_issue_falls_back_to_category_default()
    test_missing_dimension_results_do_not_break_evaluation()
    test_no_issues_produces_empty_result()
    print("All tests passed.")

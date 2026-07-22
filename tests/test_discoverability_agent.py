"""Unit tests for :class:`DiscoverabilityAgent`.

Covers a perfectly discoverable website, each individual criterion
failing in isolation, and a website with nothing discoverable at all.
The agent consumes only a `WebsiteEvidence` instance built by hand
here — no network access, HTML parsing, or other evidence-collection
tool is exercised by these tests.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running this file directly (e.g. from an IDE "Run" button) by
# ensuring the project root is importable, not just the `tests/` folder.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.discoverability_agent import DiscoverabilityAgent
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


def _perfect_evidence() -> WebsiteEvidence:
    """Build a `WebsiteEvidence` that should pass every criterion."""
    return WebsiteEvidence(
        url=URL,
        status_code=200,
        robots_txt="User-agent: *\nSitemap: https://www.example.com/sitemap.xml",
        sitemap_xml="<urlset></urlset>",
        llms_txt="# Example\n\n> A sample site.",
        title="Example Site",
        meta_tags={"description": "A sample site for testing."},
        canonical="https://www.example.com/",
        open_graph={"og:title": "Example Site", "og:description": "A sample site."},
        internal_links=["https://www.example.com/about", "https://www.example.com/contact"],
        api_analysis={
            "openapi_urls": ["https://www.example.com/openapi.json"],
            "swagger_urls": [],
            "redoc_urls": [],
            "api_documentation_urls": [],
            "api_endpoints": [],
            "graphql_endpoints": [],
        },
    )


def test_perfect_website_scores_100() -> None:
    """Every criterion passes: the score should be exactly 100."""
    agent = DiscoverabilityAgent()

    result = agent.evaluate(_perfect_evidence())
    _print_result("perfect website", result)

    assert result.score == 100.0
    assert all(result.checks.values())
    assert result.issues == []
    assert result.recommendations == []
    assert result.details["title"] == "Example Site"
    assert result.details["canonical"] == "https://www.example.com/"


def test_missing_robots_txt() -> None:
    """robots.txt absent: only that criterion fails."""
    agent = DiscoverabilityAgent()
    evidence = _perfect_evidence()
    evidence.robots_txt = None

    result = agent.evaluate(evidence)
    _print_result("missing robots.txt", result)

    assert result.checks["robots_txt"] is False
    assert "No robots.txt found" in result.issues
    assert result.score == round(6 / 7 * 100, 2)


def test_missing_sitemap() -> None:
    """sitemap.xml absent: only that criterion fails."""
    agent = DiscoverabilityAgent()
    evidence = _perfect_evidence()
    evidence.sitemap_xml = None

    result = agent.evaluate(evidence)
    _print_result("missing sitemap.xml", result)

    assert result.checks["sitemap"] is False
    assert "No sitemap.xml found" in result.issues
    assert result.score == round(6 / 7 * 100, 2)


def test_missing_llms_txt() -> None:
    """llms.txt absent: only that criterion fails."""
    agent = DiscoverabilityAgent()
    evidence = _perfect_evidence()
    evidence.llms_txt = None

    result = agent.evaluate(evidence)
    _print_result("missing llms.txt", result)

    assert result.checks["llms_txt"] is False
    assert "No llms.txt found" in result.issues
    assert result.score == round(6 / 7 * 100, 2)


def test_no_metadata() -> None:
    """Title, description, and canonical all absent: metadata fails."""
    agent = DiscoverabilityAgent()
    evidence = _perfect_evidence()
    evidence.title = None
    evidence.meta_tags = {}
    evidence.canonical = None

    result = agent.evaluate(evidence)
    _print_result("no metadata", result)

    assert result.checks["metadata"] is False
    assert any("Missing metadata" in issue for issue in result.issues)
    assert result.score == round(6 / 7 * 100, 2)


def test_no_open_graph() -> None:
    """No Open Graph tags: only that criterion fails."""
    agent = DiscoverabilityAgent()
    evidence = _perfect_evidence()
    evidence.open_graph = {}

    result = agent.evaluate(evidence)
    _print_result("no Open Graph", result)

    assert result.checks["open_graph"] is False
    assert "No Open Graph metadata found" in result.issues
    assert result.score == round(6 / 7 * 100, 2)


def test_no_api_discoverability() -> None:
    """No machine-readable API surface: only that criterion fails."""
    agent = DiscoverabilityAgent()
    evidence = _perfect_evidence()
    evidence.api_analysis = {
        "openapi_urls": [],
        "swagger_urls": [],
        "redoc_urls": [],
        "api_documentation_urls": [],
        "api_endpoints": [],
        "graphql_endpoints": [],
    }

    result = agent.evaluate(evidence)
    _print_result("no API discoverability", result)

    assert result.checks["api_discoverability"] is False
    assert "No API documentation found" in result.issues
    assert result.score == round(6 / 7 * 100, 2)


def test_no_internal_links() -> None:
    """No internal navigation links: only that criterion fails."""
    agent = DiscoverabilityAgent()
    evidence = _perfect_evidence()
    evidence.internal_links = []

    result = agent.evaluate(evidence)
    _print_result("no internal links", result)

    assert result.checks["internal_links"] is False
    assert "No internal navigation links found" in result.issues
    assert result.score == round(6 / 7 * 100, 2)


def test_everything_missing_scores_near_zero() -> None:
    """A bare, empty evidence record should score at (or near) zero."""
    agent = DiscoverabilityAgent()
    evidence = WebsiteEvidence(url=URL)

    result = agent.evaluate(evidence)
    _print_result("everything missing", result)

    assert result.score == 0.0
    assert all(passed is False for passed in result.checks.values())
    assert len(result.issues) == 7
    assert len(result.recommendations) == 7


if __name__ == "__main__":
    test_perfect_website_scores_100()
    test_missing_robots_txt()
    test_missing_sitemap()
    test_missing_llms_txt()
    test_no_metadata()
    test_no_open_graph()
    test_no_api_discoverability()
    test_no_internal_links()
    test_everything_missing_scores_near_zero()
    print("All tests passed.")

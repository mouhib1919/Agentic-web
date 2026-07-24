"""Interaction Agent.

This module is the third analysis ("judgment") layer of ARAS. It
evaluates how easily an AI agent can interact with a website through
available machine-readable and actionable interfaces: backend REST API
endpoints, API documentation (OpenAPI, Swagger, ReDoc), GraphQL,
Model Context Protocol (MCP) endpoints and tools/resources, and
frontend interaction capabilities discovered via static JavaScript
analysis.

This agent MUST NOT:
    - perform HTTP requests
    - parse HTML
    - crawl websites
    - inspect JavaScript files
    - discover APIs
    - use BeautifulSoup, HttpClient, or any extraction tool

It only reads an already-collected `WebsiteEvidence` snapshot and
turns it into a scored `InteractionResult`. Evidence collection
belongs to the Evidence Collector, a separate, earlier layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from models.evidence import WebsiteEvidence
from models.interaction import InteractionResult

_CRITERIA_COUNT = 6
_CRITERION_WEIGHT = 100.0 / _CRITERIA_COUNT


@dataclass(frozen=True)
class _CriterionOutcome:
    """The result of evaluating a single interaction criterion.

    Attributes:
        passed: Whether the criterion was satisfied.
        details: Evidence to merge into `InteractionResult.details`.
        issue: Message to record if the criterion failed.
        recommendation: Fix to record if the criterion failed.
    """

    passed: bool
    details: dict[str, object]
    issue: str
    recommendation: str


class InteractionAgent:
    """Evaluates a website's interactivity for AI agents.

    This class holds no evidence-collection logic. It is a pure
    judgment step: it reads a `WebsiteEvidence` snapshot and scores it
    against a fixed set of equally-weighted interaction criteria.
    """

    def evaluate(self, evidence: WebsiteEvidence) -> InteractionResult:
        """Evaluate interaction capability from already-collected evidence.

        Args:
            evidence: The `WebsiteEvidence` snapshot to evaluate.

        Returns:
            An `InteractionResult` with a score in [0, 100], a
            pass/fail breakdown, supporting details, and
            recommendations for every failed criterion.
        """
        result = InteractionResult()

        criteria: list[tuple[str, Callable[[WebsiteEvidence], _CriterionOutcome]]] = [
            ("api_availability", self._evaluate_api_availability),
            ("api_documentation", self._evaluate_api_documentation),
            ("graphql", self._evaluate_graphql),
            ("mcp_endpoint", self._evaluate_mcp_endpoint),
            ("mcp_tools", self._evaluate_mcp_tools),
            ("frontend_interaction", self._evaluate_frontend_interaction),
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
        name: str, outcome: _CriterionOutcome, result: InteractionResult
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
    # 1. Backend API availability
    # ------------------------------------------------------------------

    @staticmethod
    def _evaluate_api_availability(evidence: WebsiteEvidence) -> _CriterionOutcome:
        """Check that an executable API interaction surface exists.

        Considers raw REST endpoints and GraphQL endpoints, since both
        are surfaces an agent could call directly. Documentation-only
        evidence (OpenAPI/Swagger/ReDoc/general docs URLs) is
        deliberately excluded and evaluated separately by
        `_evaluate_api_documentation`: publishing a spec does not by
        itself prove a callable endpoint exists, so counting it here
        would double-credit the same evidence across two criteria.

        Args:
            evidence: The evidence snapshot to evaluate.

        Returns:
            The outcome of this criterion.
        """
        api_endpoints = evidence.api_analysis.get("api_endpoints") or []
        graphql_endpoints = evidence.api_analysis.get("graphql_endpoints") or []
        found = bool(api_endpoints or graphql_endpoints)

        return _CriterionOutcome(
            passed=found,
            details={"api_endpoints": api_endpoints, "graphql_endpoints": graphql_endpoints},
            issue="No executable API interaction surface detected.",
            recommendation="Expose structured API endpoints (REST or GraphQL) that agents can consume.",
        )

    # ------------------------------------------------------------------
    # 2. API documentation availability
    # ------------------------------------------------------------------

    @staticmethod
    def _evaluate_api_documentation(evidence: WebsiteEvidence) -> _CriterionOutcome:
        """Check that at least one API documentation surface was discovered.

        Considers OpenAPI, Swagger, ReDoc, and general API documentation
        URLs, as recorded in `evidence.api_analysis`.

        Args:
            evidence: The evidence snapshot to evaluate.

        Returns:
            The outcome of this criterion.
        """
        api_analysis = evidence.api_analysis
        openapi_urls = api_analysis.get("openapi_urls") or []
        swagger_urls = api_analysis.get("swagger_urls") or []
        redoc_urls = api_analysis.get("redoc_urls") or []
        api_documentation_urls = api_analysis.get("api_documentation_urls") or []

        found = bool(openapi_urls or swagger_urls or redoc_urls or api_documentation_urls)

        return _CriterionOutcome(
            passed=found,
            details={
                "openapi_urls": openapi_urls,
                "swagger_urls": swagger_urls,
                "redoc_urls": redoc_urls,
                "api_documentation_urls": api_documentation_urls,
            },
            issue="No API documentation available.",
            recommendation="Publish OpenAPI, Swagger, or API documentation.",
        )

    # ------------------------------------------------------------------
    # 3. GraphQL availability
    # ------------------------------------------------------------------

    @staticmethod
    def _evaluate_graphql(evidence: WebsiteEvidence) -> _CriterionOutcome:
        """Check that a GraphQL endpoint was discovered.

        Args:
            evidence: The evidence snapshot to evaluate.

        Returns:
            The outcome of this criterion.
        """
        graphql_endpoints = evidence.api_analysis.get("graphql_endpoints") or []
        found = bool(graphql_endpoints)

        return _CriterionOutcome(
            passed=found,
            details={"graphql_endpoints": graphql_endpoints},
            issue="No GraphQL endpoint detected.",
            recommendation="Expose GraphQL APIs when flexible agent interaction is required.",
        )

    # ------------------------------------------------------------------
    # 4. MCP endpoint availability
    # ------------------------------------------------------------------

    @staticmethod
    def _evaluate_mcp_endpoint(evidence: WebsiteEvidence) -> _CriterionOutcome:
        """Check that a Model Context Protocol endpoint was discovered.

        Args:
            evidence: The evidence snapshot to evaluate.

        Returns:
            The outcome of this criterion.
        """
        mcp_endpoints = evidence.api_analysis.get("mcp_endpoints") or []
        found = bool(mcp_endpoints)

        return _CriterionOutcome(
            passed=found,
            details={"mcp_endpoints": mcp_endpoints},
            issue="No MCP endpoint detected.",
            recommendation="Provide MCP interfaces to expose agent-native capabilities.",
        )

    # ------------------------------------------------------------------
    # 5. MCP tools and resources
    # ------------------------------------------------------------------

    @staticmethod
    def _evaluate_mcp_tools(evidence: WebsiteEvidence) -> _CriterionOutcome:
        """Check that explicit MCP tools or resources were discovered.

        Args:
            evidence: The evidence snapshot to evaluate.

        Returns:
            The outcome of this criterion.
        """
        mcp_tools = evidence.api_analysis.get("mcp_tools") or []
        mcp_resources = evidence.api_analysis.get("mcp_resources") or []
        found = bool(mcp_tools or mcp_resources)

        return _CriterionOutcome(
            passed=found,
            details={"mcp_tools": mcp_tools, "mcp_resources": mcp_resources},
            issue="No MCP tools or resources available.",
            recommendation="Expose MCP tools and resources describing available actions.",
        )

    # ------------------------------------------------------------------
    # 6. Frontend interaction capabilities
    # ------------------------------------------------------------------

    @staticmethod
    def _evaluate_frontend_interaction(evidence: WebsiteEvidence) -> _CriterionOutcome:
        """Check that the frontend exposes actionable interaction capabilities.

        Considers API references, GraphQL references, and WebSocket
        references discovered via static analysis of the frontend
        JavaScript, as recorded in `evidence.frontend_analysis`.

        Args:
            evidence: The evidence snapshot to evaluate.

        Returns:
            The outcome of this criterion.
        """
        frontend_analysis = evidence.frontend_analysis
        api_urls = frontend_analysis.get("discovered_api_urls") or []
        graphql_references = frontend_analysis.get("graphql_references") or []
        websocket_references = frontend_analysis.get("websocket_references") or []

        frontend_actions = [*api_urls, *graphql_references, *websocket_references]
        found = bool(frontend_actions)

        return _CriterionOutcome(
            passed=found,
            details={"frontend_actions": frontend_actions},
            issue="No actionable frontend interaction detected.",
            recommendation="Expose structured actions or machine-readable interaction surfaces.",
        )

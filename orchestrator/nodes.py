"""LangGraph node functions for the ARAS orchestration workflow.

Each node is a thin adapter between the shared `ARASState` and one
already-implemented agent. A node's only responsibilities are:
reading its required input from the state, calling the corresponding
agent, and returning a partial state update. No evaluation, scoring,
or evidence-collection logic is implemented here — it is delegated
entirely to the existing agent classes.

Any exception raised by an agent is caught and recorded in
`state.errors` rather than propagated, so a single agent failure
never aborts the rest of the workflow.
"""

from __future__ import annotations

from typing import Any, Callable

from agents.comprehension_agent import ComprehensionAgent
from agents.discoverability_agent import DiscoverabilityAgent
from agents.evidence_collector import EvidenceCollectorAgent
from agents.interaction_agent import InteractionAgent
from agents.reporter_agent import ReporterAgent
from agents.rule_engine import RuleEngine
from agents.scoring_agent import ScoringAgent
from agents.security_agent import SecurityAgent
from models.evidence import WebsiteEvidence
from orchestrator.state import ARASState
from recommendation.agent import RecommendationAgent
from recommendation.rag.retriever import KnowledgeRetriever
from recommendation.rag.vector_store import VectorStoreManager

# ---------------------------------------------------------------------------
# Evidence Collector node
# ---------------------------------------------------------------------------


def evidence_collector_node(state: ARASState) -> dict[str, Any]:
    """Collect raw evidence for `state.url` via the Evidence Collector Agent.

    Args:
        state: The current workflow state. Only `url` is read.

    Returns:
        A partial state update setting `evidence` (or `None`, with a
        message appended to `errors`, if collection fails outright).
    """
    url = state["url"]
    try:
        evidence = EvidenceCollectorAgent().collect(url)
    except Exception as exc:  # noqa: BLE001 - isolate agent failure from the graph
        return {"evidence": None, "errors": [f"evidence_collector: {exc}"]}
    return {"evidence": evidence}


# ---------------------------------------------------------------------------
# Shared helper for analysis nodes
# ---------------------------------------------------------------------------


def _run_analysis_node(
    state: ARASState,
    result_key: str,
    agent_factory: Callable[[], Any],
) -> dict[str, Any]:
    """Run a single analysis agent against `state.evidence`.

    Shared by every analysis node (Discoverability, Comprehension,
    Interaction, Security): each only differs by which agent class it
    instantiates and which state field it populates.

    Args:
        state: The current workflow state. Only `evidence` is read.
        result_key: The `ARASState` field to populate with the agent's
            result (e.g. `"discoverability_result"`).
        agent_factory: A zero-argument callable constructing the agent
            to run, exposing an `evaluate(evidence)` method.

    Returns:
        A partial state update setting `result_key` (or `None`, with a
        message appended to `errors`, if evidence is unavailable or
        evaluation fails).
    """
    evidence: WebsiteEvidence | None = state.get("evidence")
    if evidence is None:
        return {
            result_key: None,
            "errors": [f"{result_key}: no evidence available to evaluate"],
        }

    try:
        result = agent_factory().evaluate(evidence)
    except Exception as exc:  # noqa: BLE001 - isolate agent failure from the graph
        return {result_key: None, "errors": [f"{result_key}: {exc}"]}

    return {result_key: result}


# ---------------------------------------------------------------------------
# Analysis nodes
# ---------------------------------------------------------------------------


def discoverability_node(state: ARASState) -> dict[str, Any]:
    """Evaluate discoverability via `DiscoverabilityAgent.evaluate()`.

    Args:
        state: The current workflow state. Only `evidence` is read.

    Returns:
        A partial state update setting `discoverability_result`.
    """
    return _run_analysis_node(state, "discoverability_result", DiscoverabilityAgent)


def comprehension_node(state: ARASState) -> dict[str, Any]:
    """Evaluate comprehension via `ComprehensionAgent.evaluate()`.

    Args:
        state: The current workflow state. Only `evidence` is read.

    Returns:
        A partial state update setting `comprehension_result`.
    """
    return _run_analysis_node(state, "comprehension_result", ComprehensionAgent)


def interaction_node(state: ARASState) -> dict[str, Any]:
    """Evaluate interaction capability via `InteractionAgent.evaluate()`.

    Args:
        state: The current workflow state. Only `evidence` is read.

    Returns:
        A partial state update setting `interaction_result`.
    """
    return _run_analysis_node(state, "interaction_result", InteractionAgent)


def security_node(state: ARASState) -> dict[str, Any]:
    """Evaluate security readiness via `SecurityAgent.evaluate()`.

    Args:
        state: The current workflow state. Only `evidence` is read.

    Returns:
        A partial state update setting `security_result`.
    """
    return _run_analysis_node(state, "security_result", SecurityAgent)


# ---------------------------------------------------------------------------
# Scoring node
# ---------------------------------------------------------------------------


def scoring_node(state: ARASState) -> dict[str, Any]:
    """Aggregate the four analysis results via `ScoringAgent.calculate()`.

    Runs after every analysis node has joined back into the graph, so
    it reads whichever `*_result` fields are available — a dimension
    left `None` by a failed analysis node still contributes to the
    aggregate (as a 0.0 score) rather than aborting scoring entirely.

    Args:
        state: The current workflow state. Reads
            `discoverability_result`, `comprehension_result`,
            `interaction_result`, and `security_result`.

    Returns:
        A partial state update setting `global_result`.
    """
    try:
        result = ScoringAgent().calculate(
            discoverability_result=state.get("discoverability_result"),
            comprehension_result=state.get("comprehension_result"),
            interaction_result=state.get("interaction_result"),
            security_result=state.get("security_result"),
        )
    except Exception as exc:  # noqa: BLE001 - isolate agent failure from the graph
        return {"global_result": None, "errors": [f"global_result: {exc}"]}

    return {"global_result": result}


# ---------------------------------------------------------------------------
# Rule Engine node
# ---------------------------------------------------------------------------


def rule_engine_node(state: ARASState) -> dict[str, Any]:
    """Classify every reported issue via `RuleEngine.evaluate()`.

    Reads the four analysis results directly (not `global_result`):
    the Rule Engine classifies individual `issues` messages, which live
    on the analysis results themselves, not on the aggregate score.

    Args:
        state: The current workflow state. Reads
            `discoverability_result`, `comprehension_result`,
            `interaction_result`, and `security_result`.

    Returns:
        A partial state update setting `rule_engine_result`.
    """
    try:
        result = RuleEngine().evaluate(
            {
                "discoverability": state.get("discoverability_result"),
                "comprehension": state.get("comprehension_result"),
                "interaction": state.get("interaction_result"),
                "security": state.get("security_result"),
            }
        )
    except Exception as exc:  # noqa: BLE001 - isolate agent failure from the graph
        return {"rule_engine_result": None, "errors": [f"rule_engine_result: {exc}"]}

    return {"rule_engine_result": result}


# ---------------------------------------------------------------------------
# Recommendation node
# ---------------------------------------------------------------------------


def recommendation_node(state: ARASState) -> dict[str, Any]:
    """Generate recommendations for every classified issue.

    Calls `RecommendationAgent.generate()` with a `KnowledgeRetriever`
    loaded from the already-persisted ChromaDB collection (built
    earlier, offline, by the ingestion + vector-store pipeline) — this
    node never builds embeddings or a vector store itself, only loads
    what already exists. If no persisted collection is found, the
    retriever is left uninitialized and `RecommendationAgent` falls
    back to generating recommendations from issue information alone
    (its own documented Case 1 behavior).

    Args:
        state: The current workflow state. Reads `rule_engine_result`.

    Returns:
        A partial state update setting `recommendation_result`.
    """
    rule_engine_result = state.get("rule_engine_result")
    if rule_engine_result is None:
        return {
            "recommendation_result": None,
            "errors": ["recommendation_result: no classified issues available"],
        }

    try:
        retriever = KnowledgeRetriever()
        try:
            retriever.initialize(str(VectorStoreManager().persist_directory))
        except FileNotFoundError:
            pass  # RecommendationAgent handles an uninitialized retriever gracefully.

        result = RecommendationAgent(retriever=retriever).generate(rule_engine_result.issues)
    except Exception as exc:  # noqa: BLE001 - isolate agent failure from the graph
        return {"recommendation_result": None, "errors": [f"recommendation_result: {exc}"]}

    return {"recommendation_result": result}


# ---------------------------------------------------------------------------
# Reporter node
# ---------------------------------------------------------------------------


def reporter_node(state: ARASState) -> dict[str, Any]:
    """Render the final PDF report via `ReporterAgent.generate()`.

    Runs last, after every other result (or `None`, for any stage that
    failed) is already in `state`. `ReporterAgent` itself tolerates
    missing sections (it notes them in the report rather than
    raising), so the report is generated even if analysis, scoring,
    classification, or recommendation generation partially failed.

    Args:
        state: The current workflow state. Reads `url`, `evidence`,
            every `*_result` field, and `errors`.

    Returns:
        A partial state update setting `report_result`.
    """
    try:
        result = ReporterAgent().generate(
            url=state["url"],
            evidence=state.get("evidence"),
            discoverability_result=state.get("discoverability_result"),
            comprehension_result=state.get("comprehension_result"),
            interaction_result=state.get("interaction_result"),
            security_result=state.get("security_result"),
            scoring_result=state.get("global_result"),
            rule_engine_result=state.get("rule_engine_result"),
            recommendation_result=state.get("recommendation_result"),
            errors=state.get("errors", []),
        )
    except Exception as exc:  # noqa: BLE001 - isolate agent failure from the graph
        return {"report_result": None, "errors": [f"report_result: {exc}"]}

    return {"report_result": result}

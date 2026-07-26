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
from agents.scoring_agent import ScoringAgent
from agents.security_agent import SecurityAgent
from models.evidence import WebsiteEvidence
from orchestrator.state import ARASState

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

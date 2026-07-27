"""LangGraph graph definition for the ARAS orchestration workflow.

Wires the node functions in `orchestrator.nodes` into a single
compiled graph:

    START -> evidence_collector -> {discoverability, comprehension,
                                     interaction, security} -> scoring
                                  -> rule_engine -> recommendation
                                  -> reporter -> END

The four analysis nodes all depend only on `evidence_collector` and
not on each other, so LangGraph schedules them concurrently. Scoring
depends on all four analysis nodes, so LangGraph only runs it once
every branch has joined back. Rule Engine, Recommendation, and
Reporter then run as a linear chain after Scoring. This module
contains no evaluation, aggregation, classification, recommendation,
or rendering logic itself — only graph wiring.
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from orchestrator.nodes import (
    comprehension_node,
    discoverability_node,
    evidence_collector_node,
    interaction_node,
    recommendation_node,
    reporter_node,
    rule_engine_node,
    scoring_node,
    security_node,
)
from orchestrator.state import ARASState

_EVIDENCE_COLLECTOR = "evidence_collector"
_DISCOVERABILITY = "discoverability"
_COMPREHENSION = "comprehension"
_INTERACTION = "interaction"
_SECURITY = "security"
_SCORING = "scoring"
_RULE_ENGINE = "rule_engine"
_RECOMMENDATION = "recommendation"
_REPORTER = "reporter"

# Every analysis node hangs off the Evidence Collector and joins back
# into the Scoring node.
_ANALYSIS_NODES: dict[str, object] = {
    _DISCOVERABILITY: discoverability_node,
    _COMPREHENSION: comprehension_node,
    _INTERACTION: interaction_node,
    _SECURITY: security_node,
}

# The remaining stages run as a straight-line chain after Scoring, each
# depending only on the previous one's output already being in state.
_LINEAR_CHAIN: list[tuple[str, object]] = [
    (_SCORING, scoring_node),
    (_RULE_ENGINE, rule_engine_node),
    (_RECOMMENDATION, recommendation_node),
    (_REPORTER, reporter_node),
]


def build_aras_graph() -> CompiledStateGraph:
    """Build and compile the ARAS orchestration graph.

    Returns:
        A compiled LangGraph graph ready to `.invoke()` with an
        initial `ARASState`.
    """
    graph = StateGraph(ARASState)

    graph.add_node(_EVIDENCE_COLLECTOR, evidence_collector_node)
    for name, node in _ANALYSIS_NODES.items():
        graph.add_node(name, node)
    for name, node in _LINEAR_CHAIN:
        graph.add_node(name, node)

    graph.add_edge(START, _EVIDENCE_COLLECTOR)
    for name in _ANALYSIS_NODES:
        graph.add_edge(_EVIDENCE_COLLECTOR, name)
        graph.add_edge(name, _SCORING)

    for index in range(len(_LINEAR_CHAIN) - 1):
        graph.add_edge(_LINEAR_CHAIN[index][0], _LINEAR_CHAIN[index + 1][0])
    graph.add_edge(_REPORTER, END)

    return graph.compile()

"""ARAS Orchestrator.

This module exposes the single public entry point of the
orchestration layer: `ARASOrchestrator`. It compiles the LangGraph
workflow once and runs it for a given URL, coordinating the Evidence
Collector Agent and every analysis agent (Discoverability,
Comprehension, Interaction, Security).

This orchestrator MUST NOT:
    - perform HTTP requests
    - parse HTML
    - extract website information
    - evaluate security, discoverability, comprehension, or interaction
    - calculate a global score
    - generate reports

Those responsibilities belong exclusively to the specialized agents it
coordinates. This class only builds the initial state, runs the
compiled graph, and returns the resulting `ARASState`.
"""

from __future__ import annotations

from orchestrator.graph import build_aras_graph
from orchestrator.state import ARASState


class ARASOrchestrator:
    """Coordinates the ARAS agents through a compiled LangGraph workflow.

    The graph is compiled once per orchestrator instance and reused
    across calls to `run`, since it holds no per-run state itself —
    all per-run state lives in the `ARASState` passed through the graph.
    """

    def __init__(self) -> None:
        """Compile the ARAS LangGraph workflow."""
        self._graph = build_aras_graph()

    def run(self, url: str) -> ARASState:
        """Run the full ARAS workflow for a single website.

        Args:
            url: The website URL to assess.

        Returns:
            The final `ARASState`, containing the collected
            `WebsiteEvidence`, every analysis agent's result (`None`
            for any agent that could not run or failed), and the
            aggregated `GlobalReadinessResult`.
        """
        initial_state: ARASState = {
            "url": url,
            "evidence": None,
            "discoverability_result": None,
            "comprehension_result": None,
            "interaction_result": None,
            "security_result": None,
            "global_result": None,
            "errors": [],
        }
        return self._graph.invoke(initial_state)

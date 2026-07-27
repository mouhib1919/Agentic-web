"""ARAS Orchestrator.

This module exposes the single public entry point of the
orchestration layer: `ARASOrchestrator`. It compiles the LangGraph
workflow once and runs it for a given URL, coordinating the full ARAS
pipeline: the Evidence Collector Agent, the four analysis agents
(Discoverability, Comprehension, Interaction, Security), the Scoring
Agent, the Rule Engine, the Recommendation Agent, and the Reporter Agent.

This orchestrator MUST NOT:
    - perform HTTP requests
    - parse HTML
    - extract website information
    - evaluate security, discoverability, comprehension, or interaction
    - calculate a global score
    - classify issues or assign priorities
    - retrieve documents or generate recommendations
    - generate PDF report content

Those responsibilities belong exclusively to the specialized agents it
coordinates. This class only builds the initial state, runs the
compiled graph, and returns the resulting `ARASState`.
"""

from __future__ import annotations

from typing import Any, Iterator

from orchestrator.graph import build_aras_graph
from orchestrator.state import ARASState


class ARASOrchestrator:
    """Coordinates the ARAS agents through a compiled LangGraph workflow.

    The graph is compiled once per orchestrator instance and reused
    across calls to `run` or `stream`, since it holds no per-run state
    itself — all per-run state lives in the `ARASState` passed through
    the graph.
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
            for any agent that could not run or failed), the
            aggregated `GlobalReadinessResult`, the classified issues
            from the Rule Engine, the generated recommendations, and
            the rendered PDF report's outcome.
        """
        return self._graph.invoke(self._build_initial_state(url))

    def stream(self, url: str) -> Iterator[tuple[str, ARASState]]:
        """Run the workflow, yielding progress after every completed node.

        This is the same compiled graph `run` uses, invoked through
        LangGraph's `stream_mode="updates"` instead of `invoke`, so
        callers (e.g. a web backend polling for progress) can report
        which stage just finished without the orchestrator gaining any
        node- or business-logic knowledge of its own — it only forwards
        what LangGraph already reports and keeps a running merge of the
        partial updates into a single up-to-date `ARASState` snapshot.

        Args:
            url: The website URL to assess.

        Yields:
            `(node_name, state_so_far)` pairs, in execution order: the
            name of the node that just completed, and the full
            `ARASState` merged so far (including that node's update).
            The last yielded `state_so_far` is equivalent to what `run`
            would have returned.
        """
        initial_state = self._build_initial_state(url)
        accumulated_state: dict[str, Any] = dict(initial_state)

        for update in self._graph.stream(initial_state, stream_mode="updates"):
            for node_name, partial_update in update.items():
                self._merge_update(accumulated_state, partial_update)
                yield node_name, accumulated_state  # type: ignore[misc]

    @staticmethod
    def _merge_update(accumulated_state: dict[str, Any], partial_update: dict[str, Any]) -> None:
        """Merge one node's partial state update into the running accumulator.

        Mirrors the reducer semantics declared on `ARASState`: `errors`
        is additive (matching its `Annotated[list[str], operator.add]`
        declaration), every other field is a plain overwrite.

        Args:
            accumulated_state: The state accumulated so far. Mutated in place.
            partial_update: The partial update returned by a single node.
        """
        for key, value in partial_update.items():
            if key == "errors":
                accumulated_state.setdefault("errors", [])
                accumulated_state["errors"] = accumulated_state["errors"] + value
            else:
                accumulated_state[key] = value

    @staticmethod
    def _build_initial_state(url: str) -> ARASState:
        """Build the initial `ARASState` for a single run.

        Args:
            url: The website URL to assess.

        Returns:
            The initial state, with every result field set to `None`
            and `errors` empty.
        """
        return {
            "url": url,
            "evidence": None,
            "discoverability_result": None,
            "comprehension_result": None,
            "interaction_result": None,
            "security_result": None,
            "global_result": None,
            "rule_engine_result": None,
            "recommendation_result": None,
            "report_result": None,
            "errors": [],
        }

"""Shared state contract for the ARAS LangGraph workflow.

This module defines the single state type threaded through every node
of the orchestration graph. It is a plain data contract: no
evaluation, aggregation, or scoring logic belongs here.
"""

from __future__ import annotations

import operator
from typing import Annotated, Optional, TypedDict

from models.comprehension import ComprehensionResult
from models.discoverability import DiscoverabilityResult
from models.evidence import WebsiteEvidence
from models.interaction import InteractionResult
from models.scoring import GlobalReadinessResult
from models.security import SecurityResult


class ARASState(TypedDict):
    """State shared across all nodes of the ARAS orchestration graph.

    Populated incrementally as the workflow progresses: the Evidence
    Collector node fills `evidence`, and each analysis node fills its
    own `*_result` field independently. Analysis nodes run in
    parallel, so `errors` uses an additive reducer (`operator.add`) —
    every node returns its own list of new error messages, and
    LangGraph concatenates them across concurrent branches rather than
    one branch's update overwriting another's.

    Attributes:
        url: The website URL to assess, as given to the orchestrator.
        evidence: The raw evidence collected for `url`, or `None` if
            collection has not run yet or failed outright.
        discoverability_result: Output of `DiscoverabilityAgent`, or
            `None` if not yet evaluated or evaluation failed.
        comprehension_result: Output of `ComprehensionAgent`, or
            `None` if not yet evaluated or evaluation failed.
        interaction_result: Output of `InteractionAgent`, or `None` if
            not yet evaluated or evaluation failed.
        security_result: Output of `SecurityAgent`, or `None` if not
            yet evaluated or evaluation failed.
        global_result: Output of `ScoringAgent`, aggregating the four
            `*_result` fields into a single Agentic Readiness score,
            or `None` if not yet computed.
        errors: Human-readable messages describing any node failure,
            accumulated across the whole run.

    Future extension point (deliberately absent for now, added once
    that agent exists):
        report_result: Output of a future Reporter Agent, rendering
            the full state into a human-facing report.
    """

    url: str
    evidence: Optional[WebsiteEvidence]
    discoverability_result: Optional[DiscoverabilityResult]
    comprehension_result: Optional[ComprehensionResult]
    interaction_result: Optional[InteractionResult]
    security_result: Optional[SecurityResult]
    global_result: Optional[GlobalReadinessResult]
    errors: Annotated[list[str], operator.add]

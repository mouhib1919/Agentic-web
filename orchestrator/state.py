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
from models.recommendation import RecommendationResult
from models.report import ReportResult
from models.rule_engine import RuleEngineResult
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
        global_result: Output of `ScoringAgent` (the "scoring result"),
            aggregating the four `*_result` fields into a single
            Agentic Readiness score, or `None` if not yet computed.
        rule_engine_result: Output of `RuleEngine`, classifying every
            issue reported by the four analysis results into a
            prioritized, topic-tagged `ClassifiedIssue` list, or
            `None` if not yet computed.
        recommendation_result: Output of `RecommendationAgent`,
            expanding each classified issue into a grounded,
            actionable recommendation via RAG retrieval + LLM
            generation, or `None` if not yet computed.
        report_result: Output of `ReporterAgent`, recording whether the
            final PDF report was rendered and where, or `None` if not
            yet attempted.
        errors: Human-readable messages describing any node failure,
            accumulated across the whole run.
    """

    url: str
    evidence: Optional[WebsiteEvidence]
    discoverability_result: Optional[DiscoverabilityResult]
    comprehension_result: Optional[ComprehensionResult]
    interaction_result: Optional[InteractionResult]
    security_result: Optional[SecurityResult]
    global_result: Optional[GlobalReadinessResult]
    rule_engine_result: Optional[RuleEngineResult]
    recommendation_result: Optional[RecommendationResult]
    report_result: Optional[ReportResult]
    errors: Annotated[list[str], operator.add]

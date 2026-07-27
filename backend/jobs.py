"""In-memory background job tracking for ARAS web demo analysis runs.

This module is the only place that knows about "jobs" and "progress
stages" — it is a thin integration layer on top of the existing,
unmodified `ARASOrchestrator`. It never analyzes websites, calculates
scores, classifies issues, or generates recommendations itself; it
only runs the orchestrator in a background thread and translates its
`stream()` output into a UI-friendly progress snapshot.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from orchestrator.agent import ARASOrchestrator

# Every LangGraph node name, grouped into the five user-facing stages
# requested for the demo UI. A stage is "done" once every node in its
# group has completed; the first stage that is not yet done is "running",
# and everything after it is "pending".
_STAGE_DEFINITIONS: list[tuple[str, str, frozenset[str]]] = [
    ("evidence", "Evidence collection", frozenset({"evidence_collector"})),
    (
        "analysis",
        "Website analysis",
        frozenset({"discoverability", "comprehension", "interaction"}),
    ),
    ("security", "Security evaluation", frozenset({"security"})),
    (
        "recommendation",
        "Recommendation generation",
        frozenset({"scoring", "rule_engine", "recommendation"}),
    ),
    ("report", "Report generation", frozenset({"reporter"})),
]


@dataclass
class Job:
    """Tracks a single ARAS analysis run's progress and final outcome.

    Attributes:
        job_id: Unique identifier for this run.
        url: The website URL being assessed.
        status: `"running"`, `"completed"`, or `"failed"`.
        completed_nodes: LangGraph node names that have finished so far.
        score: The final global ARAS score, once available.
        high: Count of HIGH-priority classified issues.
        medium: Count of MEDIUM-priority classified issues.
        low: Count of LOW-priority classified issues.
        recommendations_count: Number of recommendations generated.
        report_filename: Basename of the generated PDF, once available.
        workflow_errors: Non-fatal error messages recorded by the
            orchestrator's own per-node error isolation.
        error: A fatal, unexpected error message, if the run itself
            crashed outside the orchestrator's normal error handling.
    """

    job_id: str
    url: str
    status: str = "running"
    completed_nodes: set[str] = field(default_factory=set)
    score: Optional[float] = None
    high: int = 0
    medium: int = 0
    low: int = 0
    recommendations_count: int = 0
    report_filename: Optional[str] = None
    workflow_errors: list[str] = field(default_factory=list)
    error: Optional[str] = None

    def stages(self) -> list[dict[str, str]]:
        """Derive the five display stages' statuses from `completed_nodes`.

        Returns:
            One dict per stage, each with `key`, `label`, and `status`
            (`"pending"`, `"running"`, or `"done"`), in pipeline order.
        """
        stages: list[dict[str, str]] = []
        frontier_found = False
        for key, label, nodes in _STAGE_DEFINITIONS:
            if nodes <= self.completed_nodes:
                status = "done"
            elif not frontier_found:
                status = "running"
                frontier_found = True
            else:
                status = "pending"
            stages.append({"key": key, "label": label, "status": status})
        return stages


_JOBS: dict[str, Job] = {}
_LOCK = threading.Lock()


def create_job(url: str) -> Job:
    """Register a new job and start running the ARAS pipeline for it.

    Args:
        url: The website URL to assess.

    Returns:
        The newly created `Job`, already registered and running in a
        background thread.
    """
    job = Job(job_id=str(uuid.uuid4()), url=url)
    with _LOCK:
        _JOBS[job.job_id] = job

    thread = threading.Thread(target=_run_job, args=(job,), daemon=True)
    thread.start()
    return job


def get_job(job_id: str) -> Optional[Job]:
    """Look up a job by id.

    Args:
        job_id: The job identifier returned by `create_job`.

    Returns:
        The `Job`, or `None` if no job with that id exists.
    """
    with _LOCK:
        return _JOBS.get(job_id)


def _run_job(job: Job) -> None:
    """Run the full ARAS workflow for `job`, updating its progress as it goes.

    Executed on a background thread. Consumes
    `ARASOrchestrator.stream()`, which itself never raises for
    per-agent failures (those are isolated into `state.errors` by the
    orchestrator's own node design) — only a truly unexpected failure
    (e.g. the graph itself failing to run) is caught here and recorded
    as a fatal `job.error`.

    Args:
        job: The job to run and update in place.
    """
    orchestrator = ARASOrchestrator()
    final_state: dict[str, Any] = {}

    try:
        for node_name, state in orchestrator.stream(job.url):
            final_state = state
            with _LOCK:
                job.completed_nodes.add(node_name)
    except Exception as exc:  # noqa: BLE001 - surface as a failed job, don't crash the thread
        with _LOCK:
            job.status = "failed"
            job.error = str(exc)
        return

    with _LOCK:
        _apply_final_state(job, final_state)
        job.status = "completed"


def _apply_final_state(job: Job, state: dict[str, Any]) -> None:
    """Copy the final ARASState's results onto `job`'s summary fields.

    Args:
        job: The job to update. Mutated in place.
        state: The fully-merged `ARASState` after the workflow finished.
    """
    scoring_result = state.get("global_result")
    if scoring_result is not None:
        job.score = scoring_result.global_score

    rule_engine_result = state.get("rule_engine_result")
    if rule_engine_result is not None:
        job.high = rule_engine_result.summary.get("HIGH", 0)
        job.medium = rule_engine_result.summary.get("MEDIUM", 0)
        job.low = rule_engine_result.summary.get("LOW", 0)

    recommendation_result = state.get("recommendation_result")
    if recommendation_result is not None:
        job.recommendations_count = len(recommendation_result.recommendations)

    report_result = state.get("report_result")
    if report_result is not None and report_result.generated:
        job.report_filename = Path(report_result.output_path).name
    elif report_result is not None and report_result.error:
        job.error = job.error or f"Report generation failed: {report_result.error}"

    job.workflow_errors = list(state.get("errors") or [])

"""Pydantic request/response schemas for the ARAS web demo API.

Pure data-shape definitions — no orchestration, job-tracking, or
agent logic belongs here.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    """Body of `POST /api/analyze`."""

    url: str = Field(..., description="Website URL to assess, e.g. https://example.com")


class AnalyzeResponse(BaseModel):
    """Response of `POST /api/analyze`: the job to poll for progress."""

    job_id: str


class StageStatus(BaseModel):
    """A single pipeline stage's display status for the progress checklist."""

    key: str
    label: str
    status: str  # "pending" | "running" | "done"


class StatusResponse(BaseModel):
    """Response of `GET /api/analyze/{job_id}/status`."""

    job_id: str
    url: str
    status: str  # "running" | "completed" | "failed"
    stages: list[StageStatus]
    score: Optional[float] = None
    high: int = 0
    medium: int = 0
    low: int = 0
    recommendations_count: int = 0
    report_url: Optional[str] = None
    workflow_errors: list[str] = Field(default_factory=list)
    error: Optional[str] = None

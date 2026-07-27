"""ARAS web demo API.

FastAPI application exposing the existing, unmodified `ARASOrchestrator`
over HTTP, and serving the static `frontend/` demo page. This module
contains no agent, LangGraph, RAG, scoring, or PDF-rendering logic — it
only validates input, starts/tracks background jobs (via `backend.jobs`),
and serves the resulting report file.

Run from the project root:

    uvicorn backend.main:app --host 0.0.0.0 --port 8000

`reports/` (where `ReporterAgent` writes PDFs) and `frontend/` are both
resolved relative to the project root, so the server must be launched
from there.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.jobs import create_job, get_job
from backend.schemas import AnalyzeRequest, AnalyzeResponse, StatusResponse

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_REPORTS_DIR = _PROJECT_ROOT / "reports"
_FRONTEND_DIR = _PROJECT_ROOT / "frontend"

app = FastAPI(title="ARAS — Agentic Readiness Assessment System", version="1.0.0")

# Permissive CORS for demo purposes: the frontend may be served from a
# different origin than the API during local development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _is_valid_url(url: str) -> bool:
    """Check that a URL is well-formed enough to attempt an ARAS run.

    Args:
        url: The URL submitted by the user.

    Returns:
        True if it has an `http`/`https` scheme and a host.
    """
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


@app.get("/api/health")
def health() -> dict[str, str]:
    """Basic liveness check for deployment platforms."""
    return {"status": "ok"}


@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    """Start a full ARAS assessment for a website.

    Args:
        request: The submitted `url`.

    Returns:
        The `job_id` to poll for progress via
        `GET /api/analyze/{job_id}/status`.

    Raises:
        HTTPException: 400 if `url` is not a well-formed http(s) URL.
    """
    if not _is_valid_url(request.url):
        raise HTTPException(
            status_code=400,
            detail="Invalid URL: must include an http:// or https:// scheme and a host.",
        )

    job = create_job(request.url)
    return AnalyzeResponse(job_id=job.job_id)


@app.get("/api/analyze/{job_id}/status", response_model=StatusResponse)
def analyze_status(job_id: str) -> StatusResponse:
    """Poll the progress and, once finished, the outcome of an analysis job.

    Args:
        job_id: The job identifier returned by `POST /api/analyze`.

    Returns:
        The job's current stage-by-stage progress, and — once
        `status` is `"completed"` — the global score, issue counts,
        recommendation count, and a download URL for the PDF report.

    Raises:
        HTTPException: 404 if no job with that id exists.
    """
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Unknown job_id.")

    report_url = f"/api/reports/{job.report_filename}" if job.report_filename else None

    return StatusResponse(
        job_id=job.job_id,
        url=job.url,
        status=job.status,
        stages=job.stages(),
        score=job.score,
        high=job.high,
        medium=job.medium,
        low=job.low,
        recommendations_count=job.recommendations_count,
        report_url=report_url,
        workflow_errors=job.workflow_errors,
        error=job.error,
    )


@app.get("/api/reports/{filename}")
def download_report(filename: str) -> FileResponse:
    """Serve a previously generated PDF report for download.

    Args:
        filename: The report's basename, as returned in
            `StatusResponse.report_url`.

    Returns:
        The PDF file, served as a downloadable attachment.

    Raises:
        HTTPException: 404 if the filename does not resolve to an
            existing file inside the reports directory (also rejects
            any path-traversal attempt).
    """
    safe_name = Path(filename).name
    resolved_path = (_REPORTS_DIR / safe_name).resolve()

    if resolved_path.parent != _REPORTS_DIR.resolve() or not resolved_path.is_file():
        raise HTTPException(status_code=404, detail="Report not found.")

    return FileResponse(
        path=resolved_path,
        media_type="application/pdf",
        filename=safe_name,
    )


# Serve the static demo frontend. Mounted last so the explicit /api/*
# routes above always take precedence over the catch-all static files.
if _FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(_FRONTEND_DIR), html=True), name="frontend")

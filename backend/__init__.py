"""Web demo integration layer for ARAS.

This package exposes the existing `ARASOrchestrator` (unchanged) through
a small FastAPI HTTP API, so the `frontend/` demo can run the full ARAS
pipeline and download the generated PDF report without any local
installation. No agent, LangGraph, RAG, or scoring logic lives here —
only request handling, background job tracking, and file serving.
"""

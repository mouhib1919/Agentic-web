# Deploying the ARAS web demo

The app is a single FastAPI service (`backend/main.py`) that serves both the
API and the static frontend (`frontend/`), so only **one** service needs to
be deployed.

## Prerequisites

- A `GROQ_API_KEY` (used by the Recommendation Agent's `GroqLLMClient`).
  Never commit it — set it as an environment variable on the hosting
  platform instead.
- `recommendation/chroma_db/` (the pre-built knowledge base vector store)
  should be committed to the repository as-is, so the deployed instance
  doesn't need to re-ingest and re-embed the knowledge base on first boot.

## Option A — Render.com (recommended, uses `render.yaml`)

1. Push this repository to GitHub/GitLab.
2. In Render: **New > Blueprint**, point it at the repo — it will read
   `render.yaml` automatically.
3. Set the `GROQ_API_KEY` environment variable in the Render dashboard
   (marked `sync: false` in `render.yaml`, so Render will prompt for it).
4. Deploy. Render builds with `pip install -r requirements.txt` and starts
   with `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`.
5. Render gives you a public URL like `https://aras-demo.onrender.com` —
   that's the link to send your supervisor.

Note: `torch` + `sentence-transformers` need noticeably more RAM than a
typical free-tier web service (512MB) comfortably allows. The `starter`
plan is set in `render.yaml`; downgrade at your own risk of OOM crashes
during embedding-model loading.

## Option B — Railway

1. Push the repo to GitHub.
2. In Railway: **New Project > Deploy from GitHub repo**.
3. Railway auto-detects the `Procfile` and Python project.
4. Add the `GROQ_API_KEY` environment variable in the Railway dashboard.
5. Deploy — Railway exposes a public `*.up.railway.app` URL.

## Option C — Any Docker-based host (Fly.io, Google Cloud Run, etc.)

A `Dockerfile` is included:

```bash
docker build -t aras-demo .
docker run -p 8000:8000 -e GROQ_API_KEY=your_key_here aras-demo
```

Push the built image to your platform of choice (Fly.io, Cloud Run, etc.)
and set `GROQ_API_KEY` as a secret/environment variable there.

## Running locally (no deployment)

```bash
pip install -r requirements.txt
# .env must contain GROQ_API_KEY=...
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Then open <http://localhost:8000> in a browser. Must be launched from the
project root so `reports/`, `recommendation/chroma_db/`, and `frontend/`
resolve correctly.

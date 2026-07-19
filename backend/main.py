"""
Minimal FastAPI app to run + smoke-test the intake endpoints locally.

STARTER ONLY — Umra extends/replaces this with the full orchestrator
(the /tools/*, /calls, /report routes). It just wires Aleks's intake router
so the /intake/doc + /specs endpoints are runnable today.

Run:
    pip install -r requirements-intake.txt uvicorn python-dotenv
    cd backend
    uvicorn main:app --reload --port 8000

Reads the repo-root .env automatically.
"""
import os
from pathlib import Path

# Load the repo-root .env so OPENAI_API_KEY / SUPABASE_* are available.
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass  # python-dotenv optional; env vars may already be exported

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

try:
    from intake_router import router as intake_router          # run from backend/
except ImportError:
    from backend.intake_router import router as intake_router  # run from repo root

app = FastAPI(title="The Negotiator — intake (starter)")

# Demo-wide CORS so the frontend (any localhost port) can call it. Tighten later.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(intake_router)


@app.get("/health")
def health():
    return {"ok": True}

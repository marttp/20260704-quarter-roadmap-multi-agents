"""FastAPI backend for the Quarter Roadmap Co-Pilot.

Serves:
  - JSON API:  GET /api/state, GET /health
  - SPA:       the built Vue 3 dashboard from frontend/ (Vite outputs to
               submission_frontend/static/spa/). Build with `cd frontend && npm run build`.

The Vue dev server (`npm run dev` in frontend/) proxies /api and /health here,
so during development run both: `make dashboard` (this FastAPI on :8080)
and `cd frontend && npm run dev` (Vite on :5173).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.tools import load_planning_state
from submission_frontend.agent_runtime import (
    agent_runtime_is_configured,
    call_agent_runtime,
    extract_briefing,
    extract_final_text,
)

# Load .env before reading any AGENT_RUNTIME_ID / GOOGLE_CLOUD_* env vars below.
# Without this, `make dashboard` silently ignores .env and falls back to
# whatever (possibly stale) values are exported in the shell — the cause of
# 403s against an old reasoningEngines id/region after a redeploy.
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
SPA_DIR = BASE_DIR / "static" / "spa"  # Vite build output (frontend/)
SPA_INDEX = SPA_DIR / "index.html"

app = FastAPI(
    title="Quarter Roadmap Co-Pilot — API + SPA",
    description="Prioritization board for PromptJang's Q3 planning.",
)

# Mount Vite's hashed asset bundles if they exist (i.e. the SPA has been built).
if (SPA_DIR / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=SPA_DIR / "assets"), name="assets")


def _build_view_model(quarter: str = "Q3-2026") -> Dict[str, Any]:
    """Compose everything the Vue app renders from the synthetic dataset."""
    state = load_planning_state(quarter)
    planning = state["planning"]
    return {
        "quarter": planning["quarter"],
        "capacity": planning["capacity_envelope"],
        "decision_required": planning.get("decision_required", []),
        "backlog": planning.get("backlog_from_past_quarters", []),
        "proposals": planning.get("proposed_for_q3", []),
        "history_averages": state["history"]["utilization"]["quarter_averages"],
        "commentary": state["history"]["utilization"]["commentary"],
    }


@app.get("/api/state")
def api_state():
    """JSON view of the planning state — consumed by the Vue app on mount."""
    return _build_view_model()


@app.get("/health")
def health():
    """Liveness probe for Cloud Run (codelab 09 deploy pattern)."""
    return {
        "status": "ok",
        "app": app.title,
        "spa_built": SPA_INDEX.exists(),
        "agent_runtime_configured": agent_runtime_is_configured(),
    }


@app.post("/api/review")
def api_review(prompt: str = "Review the Q3 plan and surface both agents' positions."):
    """Run the agent review.

    - If `AGENT_RUNTIME_ID` + `GOOGLE_CLOUD_PROJECT` are set (post-deploy), call
      Agent Runtime's :query endpoint and return the live PlanningBriefing.
    - Otherwise, fall back to the synthetic planning state (both agents'
      positions are read from the dataset) so local dev works pre-deploy.
    """
    if agent_runtime_is_configured():
        try:
            raw = call_agent_runtime(prompt)
            briefing = extract_briefing(raw)
            if briefing is not None:
                return {"mode": "live", "briefing": briefing, "raw": raw}
            return {
                "mode": "live_unparsed",
                "raw": raw,
                "note": "Agent responded but briefing shape was unrecognized.",
            }
        except Exception as exc:  # noqa: BLE001 — surface the failure to the UI
            return {"mode": "live_error", "error": str(exc)}
    # Synthetic fallback: the dataset already encodes both agents' positions.
    return {"mode": "synthetic", "state": _build_view_model()}


@app.post("/api/chat")
def api_chat(body: dict):
    """Free-form chat with the advisor agent.

    Sends the user's question to Agent Runtime; the workflow's classify_input_node
    routes it to the advisor_agent (which has data tools). Returns the agent's
    text answer.
    """
    question = (body or {}).get("question", "").strip()
    if not question:
        return {"mode": "error", "error": "No question provided."}

    if agent_runtime_is_configured():
        try:
            raw = call_agent_runtime(question)
            # The advisor's free-form answer is the last event's text.
            answer = extract_final_text(raw)
            return {"mode": "live", "answer": answer, "raw": raw}
        except Exception as exc:  # noqa: BLE001
            return {"mode": "live_error", "error": str(exc)}
    return {
        "mode": "synthetic",
        "answer": (
            "Advisor agent is not deployed yet. Once you run `make deploy-agent-runtime`, "
            "I can answer questions like 'who can I move to the Delivery team?' using the "
            "live org + utilization data."
        ),
    }


@app.get("/")
def spa_index():
    """Serve the built Vue SPA's index.html."""
    if not SPA_INDEX.exists():
        return JSONResponse(
            status_code=503,
            content={
                "error": "SPA not built.",
                "fix": "Run `cd frontend && npm install && npm run build`, then restart.",
            },
        )
    return FileResponse(SPA_INDEX)


@app.get("/{path:path}")
def spa_catch_all(path: str):
    """Client-side routing fallback — serve index.html for any non-API path.

    Declared last so /api/state, /health, /assets, and / take precedence.
    """
    # If the request maps to a real file in the SPA dir, serve it directly.
    candidate = SPA_DIR / path
    if candidate.is_file():
        return FileResponse(candidate)
    if not SPA_INDEX.exists():
        return JSONResponse(
            status_code=503,
            content={
                "error": "SPA not built.",
                "fix": "Run `cd frontend && npm run build`.",
            },
        )
    return FileResponse(SPA_INDEX)

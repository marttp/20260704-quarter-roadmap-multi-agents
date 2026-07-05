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

import json
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
    extract_agent_positions,
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
def api_review(body: dict | None = None):
    """Run the live agent review.

    - If `AGENT_RUNTIME_ID` + `GOOGLE_CLOUD_PROJECT` are set (post-deploy), call
      Agent Runtime and return each item's fresh planning_agent + stakeholder_agent
      positions, keyed by item_id, so the UI can overwrite the static dataset text.
    - `body` may carry the human's current board state:
      {"already_committed": [item_id, ...], "committed_hours": int}. When present,
      the agents reason only about the remaining items against the remaining
      budget (see app/agent.py's load_planning_state_node) instead of replaying
      the original scenario every time.
    - Otherwise, fall back to the synthetic planning state (both agents'
      positions are read from the dataset) so local dev works pre-deploy.
    """
    body = body or {}
    already_committed = body.get("already_committed") or []
    committed_hours = body.get("committed_hours") or 0
    if already_committed:
        prompt = json.dumps(
            {"already_committed": already_committed, "committed_hours": committed_hours}
        )
    else:
        prompt = "Review the Q3 plan and surface both agents' positions."

    if agent_runtime_is_configured():
        try:
            raw = call_agent_runtime(prompt)
            positions = extract_agent_positions(raw)
            # An empty dict is a legitimate outcome (everything's already
            # committed, so both agents correctly returned no positions) as
            # long as the agents actually ran. Only flag "unparsed" if there
            # were no events at all, which means the call itself came back empty.
            if raw.get("events"):
                return {"mode": "live", "positions": positions, "session_id": raw.get("session_id")}
            return {
                "mode": "live_unparsed",
                "raw": raw,
                "note": "Agent Runtime returned no events.",
            }
        except Exception as exc:  # noqa: BLE001 — surface the failure to the UI
            return {"mode": "live_error", "error": str(exc)}
    # Synthetic fallback: the dataset already encodes both agents' positions.
    return {"mode": "synthetic", "state": _build_view_model()}


def _build_advisor_message(question: str, already_committed: list, committed_hours: int) -> str:
    """Prefix the question with the current Q3 commit status so the advisor
    reasons about what's actually already decided, not just the original
    static scenario. Kept as plain text (not JSON) since this path must stay
    a genuine question the LLM reads — the advisor's own tools can look up
    the total budget, we just state the facts the dashboard already knows.
    """
    if not already_committed:
        return question
    items_str = ", ".join(already_committed)
    return (
        f"[Context: the human has already committed {len(already_committed)} item(s) "
        f"to Q3 ({items_str}), totaling {committed_hours}h so far. Use read_initiatives_tool "
        "to check the remaining budget before answering.] "
        f"{question}"
    )


@app.post("/api/chat")
def api_chat(body: dict):
    """Free-form chat with the advisor agent.

    Sends the user's question (prefixed with the current Q3 commit status, if
    any) to Agent Runtime; the workflow's classify_input_node routes it to the
    advisor_agent (which has data tools). Returns the agent's text answer.
    """
    body = body or {}
    question = (body.get("question") or "").strip()
    if not question:
        return {"mode": "error", "error": "No question provided."}

    already_committed = body.get("already_committed") or []
    committed_hours = body.get("committed_hours") or 0
    message = _build_advisor_message(question, already_committed, committed_hours)

    if agent_runtime_is_configured():
        try:
            raw = call_agent_runtime(message)
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

"""FastAPI dashboard for the Quarter Roadmap Co-Pilot (codelab 09 pattern).

Two columns (Backlog | Proposed for Q3) + a Q3 Committed tray. Each
decision_required item shows both agents' positions side-by-side; the human
makes the final call via [Prioritize] / [Deprioritize] / [Unblock] / [Cut].

Tier-1 (this file): renders the synthetic planning state — always works,
no API key needed. The live agent run is demonstrated via `agents-cli
playground` (codelab 06) in the video; this dashboard consumes the same
planning state the agents read.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.tools import load_planning_state

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="Quarter Roadmap Co-Pilot — Dashboard",
    description="Prioritization board for PromptJang's Q3 planning.",
)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


def _build_view_model(quarter: str = "Q3-2026") -> Dict[str, Any]:
    """Compose everything the template renders from the synthetic dataset."""
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


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    """Render the prioritization board."""
    return templates.TemplateResponse(
        "index.html",
        {"request": request, **_build_view_model()},
    )


@app.get("/api/state")
def api_state():
    """JSON view of the planning state (for client-side interactivity)."""
    return _build_view_model()


@app.get("/health")
def health():
    """Liveness probe for Cloud Run (codelab 09 deploy pattern)."""
    return {"status": "ok", "app": app.title}

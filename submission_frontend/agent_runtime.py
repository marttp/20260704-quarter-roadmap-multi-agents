"""Agent Runtime REST client — calls the deployed ADK agent via its native
``:query`` / ``:streamQuery`` contract (the ``{class_method, input}`` shape
served by ``app/app_utils/reasoning_engine_adapter.py``).

On Cloud Run, Application Default Credentials (ADC) resolve via the metadata
server using the runtime SA (must have roles/aiplatform.user). Locally,
`gcloud auth application-default login` provides ADC.

If AGENT_RUNTIME_ID is unset (local dev before the agent is deployed), callers
should fall back to the synthetic planning state — see submission_frontend/main.py.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

import google.auth
import google.auth.transport.requests
import requests

DASHBOARD_USER_ID = "dashboard-user"


def _service_base_url() -> str:
    """Build the Agent Runtime resource URL (no :query/:streamQuery suffix)."""
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    runtime_id = os.environ.get("AGENT_RUNTIME_ID")
    if not (project and runtime_id):
        raise RuntimeError(
            "AGENT_RUNTIME_ID and GOOGLE_CLOUD_PROJECT must be set to call Agent Runtime. "
            "Run `agents-cli deploy` and copy the runtime id from deployment_metadata.json."
        )

    # If AGENT_RUNTIME_ID is a full resource name path, parse project, location, and engine ID
    if "projects/" in runtime_id:
        parts = runtime_id.split("/")
        project = parts[1]
        location = parts[3]
        engine_id = parts[5]
    else:
        location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-west1")
        engine_id = runtime_id

    return (
        f"https://{location}-aiplatform.googleapis.com/v1/projects/{project}/"
        f"locations/{location}/reasoningEngines/{engine_id}"
    )


def _access_token() -> str:
    """Fetch an OAuth access token via Application Default Credentials."""
    creds, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    if not creds.valid:
        creds.refresh(google.auth.transport.requests.Request())
    return creds.token  # type: ignore[no-any-return]


def agent_runtime_is_configured() -> bool:
    """True if the env vars needed to reach Agent Runtime are set."""
    return bool(
        os.environ.get("AGENT_RUNTIME_ID") and os.environ.get("GOOGLE_CLOUD_PROJECT")
    )


def _create_session(base_url: str, headers: Dict[str, str], user_id: str) -> str:
    """Create an Agent Runtime session via the ``async_create_session`` class method."""
    resp = requests.post(
        f"{base_url}:query",
        headers=headers,
        json={"class_method": "async_create_session", "input": {"user_id": user_id}},
        timeout=30,
    )
    resp.raise_for_status()
    session_id = resp.json().get("output", {}).get("id")
    if not session_id:
        raise RuntimeError("Agent Runtime returned a session with no id.")
    return session_id


def call_agent_runtime(
    prompt: str = "Review the Q3 plan and surface both agents' positions.",
    user_id: str = DASHBOARD_USER_ID,
) -> Dict[str, Any]:
    """Run the deployed workflow via ``async_create_session`` + ``async_stream_query``.

    This mirrors exactly what `agents-cli run --mode adk` does against Agent
    Runtime (verified working): create a session with a plain :query call,
    then stream the message via :streamQuery. The response is newline-delimited
    JSON events (ADK's standard `{author, content: {parts: [{text}]}}` shape).
    """
    base_url = _service_base_url()
    headers = {
        "Authorization": f"Bearer {_access_token()}",
        "Content-Type": "application/json",
    }

    session_id = _create_session(base_url, headers, user_id)

    payload = {
        "class_method": "async_stream_query",
        "input": {"user_id": user_id, "session_id": session_id, "message": prompt},
    }

    events: List[Dict[str, Any]] = []
    with requests.post(
        f"{base_url}:streamQuery", headers=headers, json=payload, stream=True, timeout=120
    ) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines(decode_unicode=True):
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    return {"events": events, "session_id": session_id}


def _event_text(event: Dict[str, Any]) -> str:
    """Concatenate the text parts of a single ADK event, or '' if none."""
    content = event.get("content")
    if not isinstance(content, dict):
        return ""
    parts = content.get("parts") or []
    texts = [p.get("text", "") for p in parts if isinstance(p, dict)]
    return "".join(t for t in texts if t)


def extract_final_text(runtime_response: Dict[str, Any]) -> str:
    """The most recent non-empty text across all streamed events (e.g. the
    advisor's answer, or the last agent's output for the review workflow)."""
    events = runtime_response.get("events", [])
    for event in reversed(events):
        text = _event_text(event)
        if text.strip():
            return text
    return "(Agent responded but no parseable text was found.)"


def extract_agent_positions(runtime_response: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Merge planning_agent + stakeholder_agent AgentPositionsOutput events into
    one dict per item_id: {item_id: {planning_position, planning_reason,
    stakeholder_position, stakeholder_reason}}.

    summarize_node (a plain function node, not an LlmAgent) doesn't emit its own
    author-tagged content event in the stream, so there's no single combined
    briefing to pull — this reconstructs the same per-item view directly from
    both agents' raw structured output.
    """
    merged: Dict[str, Dict[str, Any]] = {}
    for event in runtime_response.get("events", []):
        author = event.get("author")
        if author not in ("planning_agent", "stakeholder_agent"):
            continue
        text = _event_text(event)
        if not text.strip():
            continue
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            continue
        positions = parsed.get("positions") if isinstance(parsed, dict) else None
        if not positions:
            continue
        prefix = "planning" if author == "planning_agent" else "stakeholder"
        for p in positions:
            item_id = p.get("item_id")
            if not item_id:
                continue
            merged.setdefault(item_id, {})
            merged[item_id][f"{prefix}_position"] = p.get("position")
            merged[item_id][f"{prefix}_reason"] = p.get("reason")
    return merged


def extract_briefing(runtime_response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Best-effort extraction of a structured (JSON) agent output from the
    streamed events — e.g. an AgentPositionsOutput or PlanningBriefing.

    Scans events newest-first since the final agent's output is the most
    complete. Returns None if nothing JSON-shaped is found — callers should
    treat that as 'fall back to synthetic state'.
    """
    events = runtime_response.get("events", [])
    for event in reversed(events):
        text = _event_text(event)
        if not text.strip():
            continue
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict) and (
            "reviews" in parsed or "decision_required" in parsed or "positions" in parsed
        ):
            return parsed
    return None

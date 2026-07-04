"""Agent Runtime REST client — calls the deployed ADK agent's :query endpoint.

Codelab 09 pattern. On Cloud Run, Application Default Credentials (ADC) resolve
via the metadata server using the runtime SA (must have roles/aiplatform.user).
Locally, `gcloud auth application-default login` provides ADC.

If AGENT_RUNTIME_ID is unset (local dev before the agent is deployed), callers
should fall back to the synthetic planning state — see submission_frontend/main.py.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

import google.auth
import google.auth.transport.requests
import requests


def _runtime_query_url() -> str:
    """Build the Agent Runtime :query URL from env vars."""
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-west1")
    runtime_id = os.environ.get("AGENT_RUNTIME_ID")
    if not (project and runtime_id):
        raise RuntimeError(
            "AGENT_RUNTIME_ID and GOOGLE_CLOUD_PROJECT must be set to call Agent Runtime. "
            "Run `agents-cli deploy` and copy the runtime id from deployment_metadata.json."
        )
    return (
        f"https://{location}-aiplatform.googleapis.com/v1/projects/{project}/"
        f"locations/{location}/agentRuntimeEnvironments/{runtime_id}:query"
    )


def _access_token() -> str:
    """Fetch an OAuth access token via Application Default Credentials."""
    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    if not creds.valid:
        creds.refresh(google.auth.transport.requests.Request())
    return creds.token  # type: ignore[no-any-return]


def agent_runtime_is_configured() -> bool:
    """True if the env vars needed to reach Agent Runtime are set."""
    return bool(os.environ.get("AGENT_RUNTIME_ID") and os.environ.get("GOOGLE_CLOUD_PROJECT"))


def call_agent_runtime(prompt: str = "Review the Q3 plan and surface both agents' positions.") -> Dict[str, Any]:
    """POST to Agent Runtime :query and return the parsed response.

    The agent (app/agent.py) runs on Agent Runtime with the bundled dataset;
    the prompt just triggers the workflow. The response shape follows the
    Agent Runtime REST schema — the workflow's PlanningBriefing lands in the
    final output.
    """
    url = _runtime_query_url()
    headers = {
        "Authorization": f"Bearer {_access_token()}",
        "Content-Type": "application/json",
    }
    # Codelab 09 wraps the user message under input.message.
    payload: Dict[str, Any] = {"input": {"message": prompt}}

    resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=120)
    resp.raise_for_status()
    return resp.json()  # caller interprets the response shape


def extract_briefing(runtime_response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Best-effort extraction of the PlanningBriefing from an Agent Runtime response.

    Agent Runtime wraps the agent output; the exact field path can vary by version,
    so we walk the common locations. Returns None if nothing shaped like a briefing
    is found — callers should treat that as 'fall back to synthetic state'.
    """
    # Common wrap locations, in order of preference.
    for path in (
        ("output",),
        ("response", "output"),
        ("result", "output"),
        ("predictions", 0, "output"),
    ):
        node: Any = runtime_response
        try:
            for key in path:
                node = node[key]
        except (KeyError, IndexError, TypeError):
            continue
        if isinstance(node, str):
            # The workflow yields briefing.model_dump_json() — try to parse.
            try:
                return json.loads(node)
            except json.JSONDecodeError:
                continue
        if isinstance(node, dict) and ("reviews" in node or "decision_required" in node):
            return node
    return None

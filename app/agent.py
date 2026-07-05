"""ADK 2.0 graph Workflow with two modes: Q3 review + free-form chat advisor.

Scenario (see app/data/README.md): PromptJang's Q3 plan over-runs the Eng initiative budget by 260h.
Four items are flagged `decision_required`. Two agents with opposing mandates debate each;
the human makes the final call in the UI.

Graph flow (dual-mode, routed by classify_input_node):

    Review mode (default; message has no '?' / question keywords):
      START -> classify_input_node
            -> load_planning_state_node   (redacts PII, formats context)
            -> planning_agent             (Eng stance)
            -> build_stakeholder_input_node
            -> stakeholder_agent          (Product stance)
            -> summarize_node             (PlanningBriefing for the UI)
            -> END

    Chat mode (message looks like a question):
      START -> classify_input_node
            -> advisor_agent              (free-form Q&A with data tools)
            -> END

The advisor_agent lets the planner ask things like "who can I move to the Delivery
team to unblock Circuit Breakers?" — it has tools to read org + utilization + initiatives.

Built on the Agent Development Kit 2.0 graph Workflow API (codelab 06 pattern).
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from google.adk.agents import LlmAgent
from google.adk.agents.context import Context
from google.adk.apps.app import App
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
from google.adk.workflow import START, Workflow, node

from app.models import (
    AgentPosition,
    AgentPositionsOutput,
    CapacityEnvelope,
    ItemReview,
    PlanningBriefing,
)
from app.tools import (
    load_org,
    load_planning_state,
    load_quarter_initiatives,
    load_utilization_history,
    redact_confidential,
)

# Default model used across all LlmAgents. Same id as codelabs 06/07/08.
DEFAULT_MODEL = "gemini-3.1-flash-lite"


# --------------------------------------------------------------------------- #
# Function nodes (deterministic Python; no LLM cost).
# Each takes (ctx, node_input), reads/writes ctx.state, and yields Event(...).
# --------------------------------------------------------------------------- #


@node
def load_planning_state_node(ctx: Context, node_input: Any):
    """Read the synthetic dataset, redact PII, format the agent context, stash in state.

    Security: `redact_confidential` runs HERE, before any downstream LlmAgent sees the text.

    node_input may carry the human's CURRENT board state as a JSON string —
    {"already_committed": [item_id, ...], "committed_hours": int} — sent by the
    dashboard's "Run live agent review" button. When present, items already
    committed are excluded from what the agents reason about (they're decided;
    re-litigating them isn't useful), and the capacity envelope reflects the
    hours already spent, so the agents debate the REMAINING budget against the
    REMAINING items, not the original static scenario every time. Plain-text
    prompts (e.g. from `agents-cli run`) fall back to the full original review.
    """
    already_committed, committed_hours = _parse_review_override(node_input)
    state = load_planning_state()
    context_json = redact_confidential(
        _format_planning_context(state, already_committed, committed_hours)
    )
    # Stash both the slim agent context (string) and the raw state (dict) for downstream nodes.
    yield Event(
        output=context_json,
        actions=EventActions(
            state_delta={"planning_context": context_json, "raw_state": state}
        ),
    )


def _extract_message_text(node_input: Any) -> str:
    """Get the plain text out of a node's input, which ADK passes as a
    genai Content object (parts=[Part(text=...)], role='user'), NOT a plain
    string. str(content) would serialize the Python repr instead of the actual
    message text — every node that needs the real text (classify_input_node,
    _parse_review_override) must go through this, not a bare str() cast.
    """
    if node_input is None:
        return ""
    if isinstance(node_input, str):
        return node_input
    parts = getattr(node_input, "parts", None)
    if parts:
        texts = [getattr(p, "text", None) for p in parts]
        return "".join(t for t in texts if t)
    return str(node_input)


def _parse_review_override(node_input: Any) -> tuple[List[str], int]:
    """Parse an optional {"already_committed": [...], "committed_hours": N} JSON
    message into (already_committed_ids, committed_hours). Returns ([], 0) for
    plain-text prompts or anything that doesn't parse as that shape.
    """
    text = _extract_message_text(node_input)
    if not text:
        return [], 0
    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return [], 0
    if not isinstance(parsed, dict):
        return [], 0
    already_committed = parsed.get("already_committed") or []
    committed_hours = parsed.get("committed_hours") or 0
    if not isinstance(already_committed, list):
        return [], 0
    return [str(i) for i in already_committed], int(committed_hours)


def _format_planning_context(
    state: Dict[str, Any],
    already_committed: List[str] | None = None,
    committed_hours: int = 0,
) -> str:
    """Build a compact JSON string the LlmAgents read as their 'user message'.

    Only the decision_required items still open are included — agents don't see
    auto-prioritized items or items the human already committed, keeping token
    cost down and focus on what actually needs a decision. Item positions/reasons
    are stripped so agents form their own rather than parroting the synthetic ones.
    """
    already_committed = already_committed or []
    planning = state["planning"]
    decision_ids = set(planning.get("decision_required", []))
    remaining_ids = decision_ids - set(already_committed)
    all_items = planning.get("backlog_from_past_quarters", []) + planning.get(
        "proposed_for_q3", []
    )

    envelope = dict(planning.get("capacity_envelope") or {})
    if already_committed:
        budget = envelope.get("initiative_capacity_hours_q3", 2400)
        remaining_budget = budget - committed_hours
        envelope["remaining_budget_hours"] = remaining_budget
        envelope["_note"] = (
            f"The human has ALREADY committed {committed_hours}h across "
            f"{len(already_committed)} item(s) ({', '.join(already_committed)}). "
            f"Only {remaining_budget}h of the {budget}h budget remains for the "
            "items below — reason about fit against THIS remaining budget, not "
            "the original total."
        )

    payload = {
        "quarter": planning.get("quarter"),
        "capacity_envelope": envelope,
        "already_committed": already_committed,
        "decision_required": sorted(remaining_ids),
        "items": [_slim_item(it) for it in all_items if it.get("id") in remaining_ids],
        "history_averages": state["history"]["utilization"]["quarter_averages"],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _slim_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """Keep only the fields the agents need to reason (drop synthetic stance fields)."""
    return {
        "id": item.get("id"),
        "name": item.get("name"),
        "origin": item.get("origin"),
        "incoming_state": item.get("incoming_state"),
        "owner_team": item.get("owner_team"),
        "effort_hours_remaining": item.get("effort_hours_remaining"),
        "decision_type": item.get("decision_type"),
        "feedback": item.get("feedback", []),
        "blocker": item.get("blocker"),
    }


# --------------------------------------------------------------------------- #
# LlmAgents.
# --------------------------------------------------------------------------- #


planning_agent = LlmAgent(
    name="planning_agent",
    model=DEFAULT_MODEL,
    instruction=(
        "You are the ENGINEERING PLANNING AGENT for PromptJang's quarterly roadmap review.\n"
        "Your mandate: protect sustainable utilization (target <=100% of weekly capacity).\n\n"
        "You receive the Q3 planning state as JSON: capacity envelope, decision_required items, "
        "their incoming_state, feedback, and Q1/Q2 utilization history.\n\n"
        "If the envelope includes `already_committed` and `remaining_budget_hours` (the human "
        "has already locked in some items on the dashboard), reason against the REMAINING budget "
        "and the REMAINING items only — do not re-litigate what's already committed. If "
        "decision_required is empty, return an empty positions list; do not invent items.\n\n"
        "For EACH decision_required item, emit one AgentPosition. Position options: "
        "prioritize, deprioritize, unblock, cut, defer_partial, auto_keep, auto_prioritize.\n"
        "Your reason MUST cite one of:\n"
        "  - the Q1/Q2 utilization history (e.g. 'Ingestion peaked at 122% in Q1 week 8'),\n"
        "  - the item's incoming_state (e.g. 'blocked on Design'), or\n"
        "  - the capacity envelope, using the remaining budget if present (e.g. 'only 340h "
        "of the remaining budget is left').\n"
        "One sentence per reason. No preamble."
    ),
    output_key="planning_positions",
    output_schema=AgentPositionsOutput,
)


@node
def build_stakeholder_input_node(ctx: Context, node_input: Any):
    """Combine the redacted planning context with Eng's positions so the Stakeholder sees both.

    This is the A2A seam: the Product agent reasons *in response to* the Eng agent's positions,
    not in isolation.
    """
    context_json = ctx.state.get("planning_context", "")
    planning_positions = ctx.state.get("planning_positions", {})
    combined = {
        "planning_context": json.loads(context_json) if context_json else {},
        "planning_agent_positions": _normalize_positions(planning_positions),
    }
    yield Event(output=json.dumps(combined, ensure_ascii=False, indent=2))


stakeholder_agent = LlmAgent(
    name="stakeholder_agent",
    model=DEFAULT_MODEL,
    instruction=(
        "You are the PRODUCT STAKEHOLDER AGENT — the 'other department' in this review.\n"
        "Your mandate: maximize customer value and protect revenue commitments.\n\n"
        "You receive the planning state AND the Eng Planning Agent's positions. If the envelope "
        "includes `already_committed` and `remaining_budget_hours`, reason against the REMAINING "
        "budget and REMAINING items only — the human already locked in the committed ones. If "
        "decision_required is empty, return an empty positions list; do not invent items.\n\n"
        "For EACH decision_required item, emit one AgentPosition. You may AGREE or DISAGREE with Eng; "
        "when you disagree, cite customer feedback, market signals, or revenue risk from the "
        "planning_context.\n"
        "Position options: prioritize, deprioritize, unblock, cut, defer_partial, auto_keep, "
        "auto_prioritize.\n"
        "One sentence per reason. No preamble."
    ),
    output_key="stakeholder_positions",
    output_schema=AgentPositionsOutput,
)


# --------------------------------------------------------------------------- #
# Final summarize node -> PlanningBriefing for the UI.
# --------------------------------------------------------------------------- #


@node
def summarize_node(ctx: Context, node_input: Any):
    """Combine both agents' positions into a PlanningBriefing the dashboard renders.

    Counts consensus vs dispute so the UI can badge items that need a human decision.
    """
    state = ctx.state.get("raw_state", {})
    planning = state.get("planning", {})

    planning_positions = _positions_by_item(ctx.state.get("planning_positions"))
    stakeholder_positions = _positions_by_item(ctx.state.get("stakeholder_positions"))

    # Build a lookup of decision_type per item.
    all_items = planning.get("backlog_from_past_quarters", []) + planning.get(
        "proposed_for_q3", []
    )
    decision_type_by_id = {
        it.get("id"): it.get("decision_type", "auto_keep") for it in all_items
    }

    reviews: List[ItemReview] = []
    consensus = 0
    dispute = 0
    for item_id in planning.get("decision_required", []):
        p = planning_positions.get(item_id)
        s = stakeholder_positions.get(item_id)
        if not p or not s:
            continue
        reviews.append(
            ItemReview(
                item_id=item_id,
                decision_type=decision_type_by_id.get(item_id, "auto_keep"),
                stakeholder_position=AgentPosition(**s),
                planning_position=AgentPosition(**p),
            )
        )
        if p.get("position") == s.get("position"):
            consensus += 1
        else:
            dispute += 1

    briefing = PlanningBriefing(
        quarter=planning.get("quarter", "Q3-2026"),
        capacity=CapacityEnvelope(**planning.get("capacity_envelope", {})),
        decision_required=planning.get("decision_required", []),
        reviews=reviews,
        consensus_count=consensus,
        dispute_count=dispute,
    )
    yield Event(output=briefing.model_dump_json())


# --------------------------------------------------------------------------- #
# Helpers: normalize the various forms an AgentPositionsOutput can take in state.
# ADK may store it as a pydantic instance, a dict, or a JSON string depending on version,
# so these helpers accept all three.
# --------------------------------------------------------------------------- #


def _normalize_positions(raw: Any) -> List[Dict[str, Any]]:
    """Return a list of {item_id, position, reason} dicts from any input shape."""
    if raw is None:
        return []
    if isinstance(raw, str):
        raw = json.loads(raw)
    if isinstance(raw, dict):
        inner = raw.get("positions", raw)
        if isinstance(inner, dict):
            inner = [inner]
        return [dict(p) for p in inner]
    if isinstance(raw, list):
        return [dict(p) for p in raw]
    # Pydantic model instance.
    if hasattr(raw, "positions"):
        return [
            p.model_dump() if hasattr(p, "model_dump") else dict(p)
            for p in raw.positions
        ]
    return []


def _positions_by_item(raw: Any) -> Dict[str, Dict[str, Any]]:
    """Index positions by item_id for O(1) lookup in summarize_node."""
    positions = {}
    for p in _normalize_positions(raw):
        item_id = p.get("item_id")
        if item_id:
            positions[str(item_id)] = p
    return positions


# --------------------------------------------------------------------------- #
# Chat mode: classify_input_node + advisor_agent (free-form Q&A with data tools).
# --------------------------------------------------------------------------- #


@node
def classify_input_node(ctx: Context, node_input: Any):
    """Route the incoming message to the review chain or the chat advisor.

    Heuristic: if the message reads like a question (has a '?' or common
    question words), treat it as a chat; otherwise default to the Q3 review.
    """
    raw = _extract_message_text(node_input)
    lowered = raw.lower()
    is_chat = any(
        kw in lowered
        for kw in (
            "?", "who ", "how ", "what ", "which ", "should ", "manage",
            "move ", "team", "can ", "could ", "why ", "when ", "reorgan",
        )
    )
    route = "chat" if is_chat else "review"
    yield Event(output=raw, actions=EventActions(route=route))


# --- Tools for the advisor agent (return JSON strings for reliable LLM parsing) ---


def read_org_tool() -> str:
    """Read the company org structure: teams (with weekly capacity) and employees
    (with roles, skills). All names are suffixed (mock). Use this to answer questions
    about who is on which team and what skills they have.
    """
    return redact_confidential(json.dumps(load_org(), ensure_ascii=False, default=str))


def read_utilization_tool() -> str:
    """Read Q1/Q2 per-team weekly utilization percentages + quarter averages.
    Use this to argue about over- or under-commitment (anything over 100% is overtime).
    """
    return json.dumps(load_utilization_history(), ensure_ascii=False)


def read_initiatives_tool(quarter: str = "Q3-2026") -> str:
    """Read the initiatives for one quarter: 'Q1-2026', 'Q2-2026', or 'Q3-2026'.
    Q1/Q2 are completed history; Q3 is the planning draft with decision_required items.
    """
    return redact_confidential(
        json.dumps(load_quarter_initiatives(quarter), ensure_ascii=False, default=str)
    )


def _advisor_tools() -> list:
    """Advisor's data tools. If MCP_SERVER_URL is set (the standalone MCP server
    deployed as its own Cloud Run service), route through it via McpToolset so
    the advisor genuinely calls out over MCP. Otherwise fall back to the direct
    in-process tools below — same data, no extra network hop or dependency.
    """
    mcp_server_url = os.environ.get("MCP_SERVER_URL")
    if mcp_server_url:
        from google.adk.tools.mcp_tool import McpToolset, StreamableHTTPConnectionParams

        return [
            McpToolset(
                connection_params=StreamableHTTPConnectionParams(
                    url=f"{mcp_server_url.rstrip('/')}/mcp"
                )
            )
        ]
    return [read_org_tool, read_utilization_tool, read_initiatives_tool]


advisor_agent = LlmAgent(
    name="advisor_agent",
    model=DEFAULT_MODEL,
    instruction=(
        "You are the ROADMAP ADVISOR for PromptJang, a webhook reliability & observability company. "
        "You answer the human planner's free-form questions about the organization, team capacity, "
        "utilization history, and the Q3 roadmap.\n\n"
        "Use your tools to read the org structure, utilization history, and Q3 initiatives data "
        "BEFORE answering. Ground every answer in the data; if the data doesn't cover something, say so.\n\n"
        "The question may start with '[Context: the human has already committed N item(s) to Q3 "
        "(ids), totaling Xh so far...]'. When present, treat those items as DECIDED — never suggest "
        "cutting, deprioritizing, or reconsidering them, and use read_initiatives_tool's "
        "capacity_envelope (total budget) minus the stated committed hours as the REMAINING budget "
        "for any capacity question. Answer strictly against that remaining budget, not the original "
        "total.\n\n"
        "For 'who can I move' or 'who can work on X' questions, follow this order: "
        "(1) if the question names or implies a specific backlog/initiative item, look it up via "
        "read_initiatives_tool first and note its owner_team — prefer recommending someone FROM that team "
        "before considering other teams; (2) among candidates, prefer people whose skills list matches the "
        "item's domain; (3) use each employee's q3_allocation_pct (% of their capacity already committed to "
        "Q3 work — lower means more room) as the concrete availability signal, not just team-level "
        "utilization. Recommend specific people by name and role and explain the tradeoff (e.g. 'Tomás "
        "Pereira (Backend Engineer, Ingestion) is the best fit — his skills include schema, and he's only "
        "55% allocated for Q3, well below Diego and Aisha').\n\n"
        "For 'how should I manage' or 'what should I prioritize' questions: cite the Q1/Q2 utilization "
        "history and the Q3 capacity envelope (over budget by 260h). Be specific about which "
        "decision_required items matter most.\n\n"
        "Answer in 3–6 sentences. Use plain language — the human is a planner, not an engineer."
    ),
    tools=_advisor_tools(),
)


# --------------------------------------------------------------------------- #
# Root workflow + App wrapper (codelab 06 pattern).
# agents-cli playground / agents-cli run / agents-cli deploy all discover this `app`.
# --------------------------------------------------------------------------- #


root_agent = Workflow(
    name="quarter_roadmap_review",
    edges=[
        # Step 1: every request enters the classifier.
        (START, classify_input_node),
        # Step 2: route by the 'route' value emitted in EventActions.
        # ADK 2.0 GA edge form: (from_node, {route_value: target_node, ...}).
        (
            classify_input_node,
            {
                "review": load_planning_state_node,
                "chat": advisor_agent,
            },
        ),
        # Review chain (linear).
        (load_planning_state_node, planning_agent),
        (planning_agent, build_stakeholder_input_node),
        (build_stakeholder_input_node, stakeholder_agent),
        (stakeholder_agent, summarize_node),
    ],
)


app = App(
    name="quarter_roadmap_copilot",
    root_agent=root_agent,
)

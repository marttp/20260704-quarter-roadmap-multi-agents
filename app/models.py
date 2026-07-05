"""Pydantic schemas for the Quarter Roadmap Co-Pilot agents.

These mirrors the shape of data/promptjang/*.json and define the structured
outputs the ADK 2.0 LlmAgents emit, so the UI receives predictable JSON to
render (codelab 06 `output_schema` pattern). Keeping schemas centralized here
means the data layer, agents, and UI all share one source of truth.
"""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field

# --- Enums (Literal aliases keep signatures readable) ---

ItemState = Literal[
    "completed",
    "in_progress",
    "partially_done",
    "blocked",
    "not_started",
    "cut",
    "planning",
]

DecisionType = Literal[
    "prioritize_vs_deprioritize",
    "unblock_vs_cut",
    "prioritize_vs_defer_partial",
    "auto_keep",
    "auto_prioritize",
]

AgentPositionLabel = Literal[
    "prioritize",
    "deprioritize",
    "unblock",
    "cut",
    "defer_partial",
    "auto_keep",
    "auto_prioritize",
]

FeedbackSource = Literal["customer", "market", "regulatory", "internal"]
FeedbackWeight = Literal["low", "medium", "high"]


# --- Item-level models (mirror data/promptjang/initiatives_q3.json) ---


class Feedback(BaseModel):
    """A single customer / market / regulatory / internal signal on an item."""

    source: FeedbackSource
    signal: str
    weight: FeedbackWeight


class PlanningItem(BaseModel):
    """One item from the Q3 planning input — either a backlog carry-over or a new proposal."""

    id: str
    name: str
    origin: Optional[str] = None
    incoming_state: ItemState
    owner_team: str
    customer_champion: Optional[str] = None
    effort_hours_remaining: int = 0
    feedback: List[Feedback] = Field(default_factory=list)
    decision_type: DecisionType
    decision_required: bool = False


class CapacityEnvelope(BaseModel):
    """The forcing-function: demand vs initiative budget, and the verdict."""

    initiative_capacity_hours_q3: int
    total_demand_hours: int
    delta_hours: int
    delta_verdict: str


# --- Agent output schemas (used as LlmAgent output_schema) ---


class AgentPosition(BaseModel):
    """One agent's position on one item. The reason must cite state, feedback, or capacity."""

    item_id: str
    position: AgentPositionLabel
    reason: str = Field(
        description=(
            "One-sentence rationale. Must reference the item's incoming_state, its feedback, "
            "or the capacity envelope."
        )
    )


class AgentPositionsOutput(BaseModel):
    """Batch output schema for an LlmAgent reviewing the decision_required items."""

    positions: List[AgentPosition]


# --- Final briefing emitted to the UI ---


class ItemReview(BaseModel):
    """Both agents' positions on one item, side by side for the human to adjudicate."""

    item_id: str
    decision_type: DecisionType
    stakeholder_position: AgentPosition
    planning_position: AgentPosition


class PlanningBriefing(BaseModel):
    """Final structured briefing the FastAPI dashboard renders."""

    quarter: str
    capacity: CapacityEnvelope
    decision_required: List[str]
    reviews: List[ItemReview]
    consensus_count: int = Field(
        description="Items where both agents take the same position."
    )
    dispute_count: int = Field(
        description="Items where agents disagree — needs a human decision."
    )

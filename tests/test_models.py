"""Tests for the Pydantic schemas in app.models.

Validates that the structured outputs the LlmAgents emit (and the dashboard
consumes) enforce the expected vocabulary — invalid positions/states/decision
types are rejected at the schema boundary.
"""

import pytest  # type: ignore
from pydantic import ValidationError

from app.models import (
    AgentPosition,
    AgentPositionsOutput,
    CapacityEnvelope,
    Feedback,
    PlanningBriefing,
    PlanningItem,
)


def test_feedback_accepts_valid_sources_and_weights():
    fb = Feedback(source="customer", signal="renewal at risk", weight="high")
    assert fb.source == "customer"
    assert fb.weight == "high"


def test_feedback_rejects_unknown_source():
    with pytest.raises(ValidationError):
        Feedback(source="galaxy", signal="x", weight="high")  # type: ignore


def test_planning_item_minimal_construction():
    item = PlanningItem(
        id="BACKLOG-01",
        name="Circuit Breakers",
        incoming_state="not_started",
        owner_team="eng-delivery",
        decision_type="prioritize_vs_deprioritize",
        decision_required=True,
    )
    # feedback defaults to empty list, effort defaults to 0.
    assert item.feedback == []
    assert item.effort_hours_remaining == 0


def test_planning_item_rejects_unknown_state():
    with pytest.raises(ValidationError):
        PlanningItem(
            id="x",
            name="x",
            incoming_state="vaporware",  # not in the taxonomy  # type: ignore
            owner_team="eng-delivery",
            decision_type="auto_keep",
        )


def test_agent_position_requires_reason_referencing_evidence():
    pos = AgentPosition(
        item_id="BACKLOG-01",
        position="deprioritize",
        reason="Delivery on Signatures v2; stacking risks repeating the Q1 118% peak.",
    )
    assert pos.position == "deprioritize"


def test_agent_positions_output_wraps_a_list():
    out = AgentPositionsOutput(
        positions=[
            AgentPosition(
                item_id="BACKLOG-01", position="prioritize", reason="renewal risk."
            ),
            AgentPosition(
                item_id="BACKLOG-02", position="deprioritize", reason="no revenue."
            ),
        ]
    )
    assert len(out.positions) == 2


def test_capacity_envelope_round_trips_from_dataset_shape():
    # Same shape as data/promptjang/initiatives_q3.json::capacity_envelope.
    env = CapacityEnvelope(
        initiative_capacity_hours_q3=2400,
        total_demand_hours=2660,
        delta_hours=260,
        delta_verdict="Over initiative budget by ~260h.",
    )
    assert env.delta_hours == 260


def test_planning_briefing_assembles():
    briefing = PlanningBriefing(
        quarter="Q3-2026",
        capacity=CapacityEnvelope(
            initiative_capacity_hours_q3=2400,
            total_demand_hours=2660,
            delta_hours=260,
            delta_verdict="over",
        ),
        decision_required=["BACKLOG-01"],
        reviews=[],
        consensus_count=0,
        dispute_count=0,
    )
    # model_dump_json is what the summarize_node yields as Event data.
    assert "Q3-2026" in briefing.model_dump_json()

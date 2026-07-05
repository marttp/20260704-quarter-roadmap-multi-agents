"""Tests for the deterministic data loaders in app.tools.

Per agents-cli scaffold guidance: assert on deterministic code, never on LLM
response content (that belongs in `agents-cli eval`).
"""

from app.tools import (
    load_org,
    load_planning_state,
    load_quarter_initiatives,
    load_utilization_history,
)


def test_load_org_has_teams_and_employees():
    org = load_org()
    assert org["company"]["name"] == "PromptJang"
    team_ids = {t["id"] for t in org["teams"]}
    assert {
        "product",
        "eng-ingestion",
        "eng-delivery",
        "eng-platform",
        "design",
    } <= team_ids
    assert len(org["employees"]) == 12
    # Every employee name carries the (mock) suffix — no real-person ambiguity.
    assert all(e["name"].endswith("(mock)") for e in org["employees"])


def test_load_utilization_history_has_both_quarters():
    hist = load_utilization_history()
    quarters = {row["quarter"] for row in hist["history"]}
    assert {"Q1-2026", "Q2-2026"} <= quarters
    # 13 weeks per quarter × 2 quarters = 26 weekly rows.
    assert len(hist["history"]) == 26
    # The Q1 Ingestion peak (122%) the Planning Agent cites must be present.
    q1_ingestion = [
        row["utilization"]["eng-ingestion"]
        for row in hist["history"]
        if row["quarter"] == "Q1-2026"
    ]
    assert max(q1_ingestion) == 122


def test_load_quarter_initiatives_for_each_quarter():
    for q, expected_status_field in (
        ("Q1-2026", "status"),
        ("Q2-2026", "status"),
        ("Q3-2026", "planning_status"),
    ):
        data = load_quarter_initiatives(q)
        assert data["quarter"] == q
        assert "initiatives" in data or "backlog_from_past_quarters" in data, q
        assert isinstance(
            data.get(expected_status_field) or data.get("quarter_outcome"), (str, dict)
        )


def test_load_planning_state_composes_everything():
    state = load_planning_state("Q3-2026")
    assert set(state.keys()) >= {"org", "history", "planning", "decision_required"}
    assert state["planning"]["quarter"] == "Q3-2026"
    # The four decision_required item ids are the demo's forcing function.
    assert state["decision_required"] == [
        "BACKLOG-01",
        "BACKLOG-02",
        "BACKLOG-03",
        "Q3-ING-01",
    ]
    # Capacity envelope must show the over-budget delta the agents cite.
    assert state["planning"]["capacity_envelope"]["delta_hours"] == 260

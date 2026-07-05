# PromptJang Synthetic Dataset

Fully synthetic, hand-curated data for the **Quarter Roadmap Co-Pilot** demo. No real PromptJang customer, employee, or financial data is represented. All employee names are suffixed `(mock)`.

## Why this data exists

Real business planning is messy. A quarter never finishes cleanly — items end up **in-progress**, **partially-done**, **blocked**, or **not-started**. The next-quarter conversation is then: *given all this half-done / stuck / untouched work + the new things we want + what customers and the market are signaling + the capacity we actually have — what do we do with each?*

That synthesis is exactly what the two AI agents (a **Product Stakeholder Agent** and an **Eng Planning Agent**) help with. For each item, they weigh **state × feedback × capacity** and debate; the human makes the final call.

The dataset is shaped so that conversation is unavoidable:
- **Q1-2026** is distant clean history (shipped / shipped-late / slipped) — the origin of two Q2 carry-overs.
- **Q2-2026** is the just-ended quarter in a realistic mess (2 completed, 1 in_progress, 1 partially_done, 1 blocked, 1 not_started).
- **Q3-2026** is the planning draft: 4 messy carry-overs + 4 new proposals, over-running the initiative budget by 260h.
- **Four items are flagged `decision_required`**, each a different decision type so the demo shows variety.

## Files

| File | Purpose | Status |
| --- | --- | --- |
| `org.json` | Company, teams (Product + 3 Eng sub-teams + Design), mock employees, function-agent stances. | Static |
| `utilization.json` | Per-team weekly utilization % for Q1 + Q2 (26 weeks) + quarter averages + commentary. | Static (history) |
| `initiatives_q1.json` | Q1-2026 initiatives — completed; 2 slipped to Q2. | Static (history) |
| `initiatives_q2.json` | Q2-2026 initiatives — JUST-ENDED, messy end-state (in_progress / partially_done / blocked / not_started). | Static (history) |
| `initiatives_q3.json` | Q3-2026 planning input — 4 messy carry-overs + 4 proposals; 4 `decision_required`. | Dynamic (agents read; UI mutates on human confirm) |
| `events.json` | Demo triggers the UI sends into the agent workflow. | Demo script |

## Status taxonomy

| Status | Meaning |
| --- | --- |
| `completed` | Shipped, done. |
| `in_progress` | Being worked now; continues into next quarter. |
| `partially_done` | Some milestones hit, some not. |
| `blocked` | Stuck on a dep (external team / vendor / design / infra). |
| `not_started` | Planned, never began (lost to capacity). |
| `cut` | Deprioritized / abandoned. |
| `planning` | (Q3 only) proposed for the next quarter; not yet committed. |

## Item schema

History items (Q1, Q2):
```json
{
  "id": "Q2-DLV-03",
  "name": "Delivery Circuit Breakers",
  "quarter": "Q2-2026",
  "owner_team": "eng-delivery",
  "owner_function": "Engineering",
  "assignees": ["erik-lindqvist"],
  "customer_champion": "marcus-okafor",
  "deps": ["Q2-DLV-02"],
  "target_week": 13,
  "planned_hours": 240,
  "actual_hours": 0,
  "status": "not_started",
  "shipped_week": null,
  "progress_pct": 0,
  "remaining_hours": 240,
  "blocker": null,
  "reason": "Capacity-lost — ...",
  "feedback": [
    { "source": "customer", "signal": "ACME filed a reliability complaint", "weight": "high" }
  ],
  "kr": "...",
  "notes": "..."
}
```

Q3 planning items add the agent-position fields:
```json
{
  "incoming_state": "not_started",            // carried state from origin quarter
  "stakeholder_position": "prioritize",        // prioritize | deprioritize | unblock | cut | defer_partial
  "stakeholder_reason": "...",
  "planning_position": "deprioritize",
  "planning_reason": "...",
  "decision_type": "prioritize_vs_deprioritize",
  "decision_required": true
}
```

## The resource story (what the agents reason over)

| Quarter | Eng Ingestion avg | Eng Delivery avg | Eng Platform avg | Outcome |
| --- | --- | --- | --- | --- |
| Q1-2026 | **112%** (peak 122%) | **107%** (peak 118%) | 95% | 2 initiatives slipped to Q2 |
| Q2-2026 | 97% | 91% | 95% | Rebalanced; but only 2 of 6 items completed — 4 carry over in messy states |
| Q3-2026 (projected if all kept) | 115% | 112% | 108% | Over initiative budget by 260h — forces decisions |

The **Planning Agent** cites the Q1 122% peak as evidence whenever the Stakeholder pushes to over-commit.

## Capacity envelope (Q3-2026)

- Eng total capacity: **4,680 h** (3 sub-teams × 13 weeks × 120 h/week).
- After on-call / BAU / support (~49%): **~2,400 h** available for initiative work.
- Demand: **2,660 h** (640h carry-over + 2,020h new proposals).
- **Delta: +260 h over the initiative budget.** The `Q3 Committed` column refuses to accept the full set — the human must move at least one item back to Backlog.

## The four decision candidates (the demo's beats)

| Item | Incoming state | Decision type | Stakeholder says | Planning says |
| --- | --- | --- | --- | --- |
| **BACKLOG-01** Circuit Breakers | `not_started` | prioritize vs deprioritize | Prioritize (renewal risk) | Deprioritize (Delivery on Signatures v2) |
| **BACKLOG-02** Ingestion debt remnant | `partially_done` | prioritize vs deprioritize *(role-reversal)* | Deprioritize (no revenue) | Prioritize (prevents Q1 repeat) |
| **BACKLOG-03** API Keys & Permissions | `blocked` | unblock vs cut | Unblock (audit gap) | Cut (cheaper to revisit Q4) |
| **Q3-ING-01** Regional Ingestion EU | `not_started` (new) | prioritize vs defer_partial | Prioritize (P0 revenue) | Defer partial (capacity) |

Each decision type exercises a different agent-reasoning path — the demo's variety comes from this, not from volume of items.

## Feedback signals (the second force)

Each item can carry a `feedback` array. Sources: `customer`, `market`, `regulatory`, `internal`. The agents read feedback alongside state and capacity when forming their positions.

Examples in the data:
- `customer` — ACME reliability complaint (on BACKLOG-01), CSV export ask (on Q2-PLT-02), EU residency blocker (on Q3-ING-01).
- `market` — competitor shipped usage-based pricing (on Q3-PLT-04), enterprise security review requires v2 signatures (on Q3-DLV-01).
- `internal` — security team audit gap (on BACKLOG-03), finance mandate (on Q3-PLT-04).

## Editing notes

- Allotting extra mock employees or initiatives: keep `id` stable, follow the schema above.
- To re-tune the conflict intensity, change `effort_hours_remaining` or `initiative_capacity_hours_q3` in `initiatives_q3.json::capacity_envelope`.
- Employee names **must** keep the `(mock)` suffix — see `org.json`.

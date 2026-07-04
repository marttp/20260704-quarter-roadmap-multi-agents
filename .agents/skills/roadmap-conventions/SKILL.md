---
name: roadmap-conventions
description: Encodes PromptJang's quarterly-roadmap conventions so agents reason
  consistently. Use when reviewing roadmap items, prioritization decisions,
  capacity envelopes, or forming agent positions on decision_required items.
---

# Roadmap Conventions Skill

## Goal
Keep both agents (Planning + Stakeholder) reasoning from the same vocabulary
and thresholds when they debate the Q3 plan, so their disagreements are about
*judgment*, not about what words mean.

## Conventions

### Status taxonomy (the messy carry-over states)
- `completed` — shipped, done.
- `in_progress` — being worked now; spills into next quarter.
- `partially_done` — some milestones hit, some not.
- `blocked` — stuck on a dep (external team / vendor / design / infra).
- `not_started` — planned, never began (lost to capacity).
- `cut` — deprioritized / abandoned.
- `planning` — proposed for the next quarter; not yet committed.

### Decision types (what each decision_required item asks)
- `prioritize_vs_deprioritize` — ship now vs defer.
- `unblock_vs_cut` — invest in clearing the blocker vs drop the feature.
- `prioritize_vs_defer_partial` — ship in full vs scope down.
- `auto_keep` / `auto_prioritize` — both agents agree; no human decision needed.

### Utilization thresholds (the Planning Agent's evidence)
- `[85%, 100%]` — healthy band.
- `>100%` — over-commitment; cite the Q1 122% peak as the cautionary precedent.
- `<85%` — under-utilization (not currently a risk in this dataset).

### Capacity envelope (the forcing function)
- Q3 initiative budget: 2,400h (after ~49% on-call / BAU).
- Demand: 2,660h (640h carry-over + 2,020h new proposals).
- Delta: +260h. At least one `decision_required` item must be deprioritized,
  cut, or deferred — the UI's Q3 Committed column refuses the full set.

### Position-label vocabulary (what the agents emit)
`prioritize | deprioritize | unblock | cut | defer_partial | auto_keep | auto_prioritize`

## Constraints
- Reasons MUST cite one of: incoming_state, feedback, or the capacity envelope.
  Vague reasons ("it's important") are not acceptable.
- Never auto-commit a decision. Every `decision_required` resolution ends at a
  human Approve gate in the dashboard.
- Employee names + `(mock)` suffixes must already be redacted before the agent
  sees any text (handled by `app.tools.redact_confidential` upstream).

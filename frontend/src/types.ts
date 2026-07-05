// Type definitions mirroring app/models.py (Pydantic) so the Vue app is type-safe
// against the FastAPI /api/state response. Keep in sync if the Pydantic schemas change.

export type ItemState =
  | 'completed'
  | 'in_progress'
  | 'partially_done'
  | 'blocked'
  | 'not_started'
  | 'cut'
  | 'planning'

export type DecisionType =
  | 'prioritize_vs_deprioritize'
  | 'unblock_vs_cut'
  | 'prioritize_vs_defer_partial'
  | 'auto_keep'
  | 'auto_prioritize'

export type AgentPositionLabel =
  | 'prioritize'
  | 'deprioritize'
  | 'unblock'
  | 'cut'
  | 'defer_partial'
  | 'auto_keep'
  | 'auto_prioritize'

export type FeedbackSource = 'customer' | 'market' | 'regulatory' | 'internal'
export type FeedbackWeight = 'low' | 'medium' | 'high'

export interface Feedback {
  source: FeedbackSource
  signal: string
  weight: FeedbackWeight
}

export interface PlanningItem {
  id: string
  name: string
  origin?: string
  incoming_state: ItemState
  owner_team: string
  customer_champion?: string | null
  effort_hours_remaining: number
  // Present only on 'prioritize_vs_defer_partial' items — the reduced hour count
  // committed when the human picks "Defer partial" instead of the full ask.
  partial_hours?: number
  // Client-side bookkeeping only (not from the API): the original full hours,
  // stashed here when a partial commit overwrites `effort_hours_remaining`, so a
  // later "undo" can restore it.
  full_hours_remaining?: number
  feedback: Feedback[]
  decision_type: DecisionType
  decision_required: boolean
  blocker?: string | null
  // Agent positions (from the synthetic dataset; replaced by live agent output when
  // the /api/review endpoint is wired to invoke the ADK workflow).
  stakeholder_position: AgentPositionLabel
  stakeholder_reason: string
  planning_position: AgentPositionLabel
  planning_reason: string
}

export interface CapacityEnvelope {
  eng_total_capacity_hours_q3: number
  initiative_capacity_hours_q3?: number
  carryover_demand_hours?: number
  new_proposal_demand_hours?: number
  total_demand_hours: number
  delta_hours: number
  delta_verdict: string
}

export interface PlanningState {
  quarter: string
  capacity: CapacityEnvelope
  decision_required: string[]
  backlog: PlanningItem[]
  proposals: PlanningItem[]
  history_averages: Record<string, Record<string, number>>
  commentary: Record<string, string>
}

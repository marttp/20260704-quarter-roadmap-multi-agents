// Thin typed fetch client for the FastAPI backend.
// All endpoints return JSON; the dashboard reads /api/state on mount.

import type { PlanningState } from './types'

export async function fetchPlanningState(): Promise<PlanningState> {
  const res = await fetch('/api/state')
  if (!res.ok) {
    throw new Error(`Failed to load planning state: ${res.status} ${res.statusText}`)
  }
  return (await res.json()) as PlanningState
}

export async function fetchHealth(): Promise<{ status: string; app: string }> {
  const res = await fetch('/health')
  if (!res.ok) throw new Error(`Health check failed: ${res.status}`)
  return (await res.json()) as { status: string; app: string }
}

export interface AgentPositions {
  planning_position?: string
  planning_reason?: string
  stakeholder_position?: string
  stakeholder_reason?: string
}

export interface ReviewResponse {
  mode: 'live' | 'live_unparsed' | 'live_error' | 'synthetic'
  positions?: Record<string, AgentPositions>
  error?: string
  note?: string
}

// Triggers a real planning_agent -> stakeholder_agent run on Agent Runtime and
// returns each item's fresh positions, keyed by item_id. `/api/review`'s
// `prompt` is a query param (FastAPI default for a plain str arg), not a JSON
// body — the default prompt is exactly what we want here, so no body is sent.
export async function runLiveReview(): Promise<ReviewResponse> {
  const res = await fetch('/api/review', { method: 'POST' })
  if (!res.ok) {
    throw new Error(`Live review failed: ${res.status} ${res.statusText}`)
  }
  return (await res.json()) as ReviewResponse
}

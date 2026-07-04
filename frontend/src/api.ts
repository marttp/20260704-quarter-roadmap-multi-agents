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

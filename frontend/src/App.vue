<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import type { PlanningItem, PlanningState } from './types'
import { fetchPlanningState } from './api'
import ItemCard from './components/ItemCard.vue'
import CapacityBanner from './components/CapacityBanner.vue'
import ChatPanel from './components/ChatPanel.vue'

const THEME_KEY = 'quarter-roadmap-copilot:theme'
type Theme = 'light' | 'dark'
const theme = ref<Theme>('light')

function applyTheme(t: Theme) {
  document.documentElement.dataset.theme = t
}

function toggleTheme() {
  theme.value = theme.value === 'light' ? 'dark' : 'light'
  applyTheme(theme.value)
  window.localStorage.setItem(THEME_KEY, theme.value)
}

// Briefly highlights whichever card just moved, so a decision reads clearly
// on screen (and on a recorded demo) instead of silently teleporting columns.
const flashingId = ref<string | null>(null)
function flash(itemId: string) {
  flashingId.value = itemId
  window.setTimeout(() => {
    if (flashingId.value === itemId) flashingId.value = null
  }, 900)
}

const state = ref<PlanningState | null>(null)
const error = ref<string | null>(null)

// Three reactive columns. Committed starts empty; the human fills it.
const backlog = ref<PlanningItem[]>([])
const proposals = ref<PlanningItem[]>([])
const committed = ref<PlanningItem[]>([])

const STORAGE_KEY = 'quarter-roadmap-copilot:decisions:v1'

interface StoredDecisions {
  quarter: string
  backlog: PlanningItem[]
  proposals: PlanningItem[]
  committed: PlanningItem[]
}

// Hours the human has actively committed via Prioritize / Unblock / Defer partial.
const committedHours = computed(() =>
  committed.value.reduce((sum, it) => sum + (it.effort_hours_remaining ?? 0), 0),
)

// Hours from items BOTH agents already agree on (decision_required === false).
// These never get a button, never move, and are always "in scope" — so they
// must count toward budget consumption from the very first render, or the
// capacity math has no relationship to reality (see CapacityBanner.vue).
const baselineHours = computed(() =>
  [...backlog.value, ...proposals.value, ...committed.value]
    .filter((it) => !it.decision_required)
    .reduce((sum, it) => sum + (it.effort_hours_remaining ?? 0), 0),
)

onMounted(async () => {
  const storedTheme = window.localStorage.getItem(THEME_KEY)
  theme.value = storedTheme === 'dark' ? 'dark' : 'light'
  applyTheme(theme.value)

  try {
    const data = await fetchPlanningState()
    state.value = data

    const stored = loadStoredDecisions(data.quarter)
    if (stored) {
      backlog.value = stored.backlog
      proposals.value = stored.proposals
      committed.value = stored.committed
    } else {
      backlog.value = data.backlog
      proposals.value = data.proposals
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  }
})

function loadStoredDecisions(quarter: string): StoredDecisions | null {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as StoredDecisions
    return parsed.quarter === quarter ? parsed : null
  } catch {
    return null
  }
}

function persistDecisions() {
  if (!state.value) return
  const payload: StoredDecisions = {
    quarter: state.value.quarter,
    backlog: backlog.value,
    proposals: proposals.value,
    committed: committed.value,
  }
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(payload))
  } catch {
    // localStorage unavailable (private browsing, quota) — demo still works, just not persisted.
  }
}

function resetDemo() {
  window.localStorage.removeItem(STORAGE_KEY)
  window.location.reload()
}

function findAndRemove(itemId: string, lists: PlanningItem[][]): PlanningItem | null {
  for (const list of lists) {
    const idx = list.findIndex((it) => it.id === itemId)
    if (idx !== -1) return list.splice(idx, 1)[0]
  }
  return null
}

type DecideAction = 'prioritize' | 'deprioritize' | 'unblock' | 'cut' | 'defer_partial'

function onDecide(payload: { itemId: string; action: DecideAction }) {
  const isBacklog = /^BACKLOG-/.test(payload.itemId)
  flash(payload.itemId)

  if (payload.action === 'prioritize' || payload.action === 'unblock') {
    const item = findAndRemove(payload.itemId, [backlog.value, proposals.value])
    if (item) committed.value.push(item)
  } else if (payload.action === 'defer_partial') {
    // Toggle: if the partial slice is already sitting in Committed, undo it —
    // restore full hours and send the item back to its origin column.
    const committedIdx = committed.value.findIndex((it) => it.id === payload.itemId)
    if (committedIdx !== -1) {
      const item = committed.value.splice(committedIdx, 1)[0]
      item.effort_hours_remaining = item.full_hours_remaining ?? item.effort_hours_remaining
      if (isBacklog) backlog.value.push(item)
      else proposals.value.push(item)
    } else {
      // Commit only the partial slice (e.g. "ship the EU endpoint, defer the rest to Q4").
      const item = findAndRemove(payload.itemId, [backlog.value, proposals.value])
      if (item) {
        item.full_hours_remaining = item.effort_hours_remaining
        item.effort_hours_remaining = item.partial_hours ?? item.effort_hours_remaining
        committed.value.push(item)
      }
    }
  } else {
    // deprioritize / cut: move back to its origin column.
    const item = findAndRemove(payload.itemId, [backlog.value, proposals.value, committed.value])
    if (item) {
      if (isBacklog) backlog.value.push(item)
      else proposals.value.push(item)
    }
  }

  persistDecisions()
}
</script>

<template>
  <header class="top">
    <h1>🗺️ Quarter Roadmap Co-Pilot <span style="color: var(--muted); font-weight: 400;">/ PromptJang</span></h1>
    <div class="meta" v-if="state">
      <span>{{ state.quarter }} · <a href="/api/state">JSON</a> · <a href="/health">health</a></span>
      <button class="theme-toggle" @click="toggleTheme" title="Toggle light / dark theme">
        {{ theme === 'light' ? '🌙 Dark' : '☀️ Light' }}
      </button>
      <button class="reset" @click="resetDemo" title="Clear decisions and reload the original Q3 plan">↺ Reset demo</button>
    </div>
  </header>

  <main v-if="error">
    <div class="error">Failed to load: {{ error }}</div>
  </main>

  <main v-else-if="state">
    <CapacityBanner :capacity="state.capacity" :committed-hours="committedHours" :baseline-hours="baselineHours" />

    <section class="columns">
      <div class="column" id="backlog">
        <h2>Backlog (from past quarters)</h2>
        <div class="sub">Carried: in_progress / partially_done / blocked / not_started</div>
        <ItemCard
          v-for="item in backlog"
          :key="item.id"
          :item="item"
          :flash="flashingId === item.id"
          @decide="onDecide"
        />
      </div>

      <div class="column" id="proposals">
        <h2>Proposed for {{ state.quarter }}</h2>
        <div class="sub">New asks from Product</div>
        <ItemCard
          v-for="item in proposals"
          :key="item.id"
          :item="item"
          :flash="flashingId === item.id"
          @decide="onDecide"
        />
      </div>

      <div class="column" id="committed">
        <h2>Q3 Committed</h2>
        <div class="sub">Final list after human decisions ({{ committed.length }} items, {{ committedHours }}h)</div>
        <p v-if="!committed.length" style="color: var(--muted); font-size: 13px;">
          Click ↑ Prioritize / Unblock on a decision card to commit it. The capacity
          envelope refuses the full set — see the banner above.
        </p>
        <ItemCard
          v-for="item in committed"
          :key="item.id"
          :item="item"
          :flash="flashingId === item.id"
          @decide="onDecide"
        />
      </div>
    </section>

    <section class="history">
      <h3>Q1 / Q2 utilization history (the Planning Agent's evidence)</h3>
      <table>
        <thead>
          <tr>
            <th>Quarter</th><th>Product</th><th>Eng / Ingestion</th>
            <th>Eng / Delivery</th><th>Eng / Platform</th><th>Outcome</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>Q1-2026</td>
            <td>{{ state.history_averages['Q1-2026']?.product }}%</td>
            <td class="high">{{ state.history_averages['Q1-2026']?.['eng-ingestion'] }}% (peak 122%)</td>
            <td class="high">{{ state.history_averages['Q1-2026']?.['eng-delivery'] }}%</td>
            <td>{{ state.history_averages['Q1-2026']?.['eng-platform'] }}%</td>
            <td>2 initiatives slipped to Q2</td>
          </tr>
          <tr>
            <td>Q2-2026</td>
            <td>{{ state.history_averages['Q2-2026']?.product }}%</td>
            <td class="healthy">{{ state.history_averages['Q2-2026']?.['eng-ingestion'] }}%</td>
            <td class="healthy">{{ state.history_averages['Q2-2026']?.['eng-delivery'] }}%</td>
            <td class="healthy">{{ state.history_averages['Q2-2026']?.['eng-platform'] }}%</td>
            <td>Rebalanced; 4 of 6 carry over in messy states</td>
          </tr>
        </tbody>
      </table>
      <p style="color: var(--muted); font-size: 12px; margin-top: 12px;">
        Q1 commentary: {{ state.commentary?.['Q1-2026'] }}
      </p>
    </section>

    <ChatPanel />
  </main>

  <main v-else>
    <div style="color: var(--muted);">Loading planning state…</div>
  </main>

  <footer>
    Quarter Roadmap Co-Pilot · capstone for the 5-Day AI Agents Intensive Vibe Coding Course with Google.
    Synthetic PromptJang data — all names are (mock). Built with Vue 3 + TypeScript + Vite.
  </footer>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import type { PlanningItem, PlanningState } from './types'
import { fetchPlanningState } from './api'
import ItemCard from './components/ItemCard.vue'
import CapacityBanner from './components/CapacityBanner.vue'
import ChatPanel from './components/ChatPanel.vue'

const state = ref<PlanningState | null>(null)
const error = ref<string | null>(null)

// Three reactive columns. Committed starts empty; the human fills it.
const backlog = ref<PlanningItem[]>([])
const proposals = ref<PlanningItem[]>([])
const committed = ref<PlanningItem[]>([])

const committedHours = computed(() =>
  committed.value.reduce((sum, it) => sum + (it.effort_hours_remaining ?? 0), 0),
)

onMounted(async () => {
  try {
    const data = await fetchPlanningState()
    state.value = data
    backlog.value = data.backlog
    proposals.value = data.proposals
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  }
})

function findAndRemove(itemId: string, lists: PlanningItem[][]): PlanningItem | null {
  for (const list of lists) {
    const idx = list.findIndex((it) => it.id === itemId)
    if (idx !== -1) return list.splice(idx, 1)[0]
  }
  return null
}

function onDecide(payload: { itemId: string; action: 'prioritize' | 'deprioritize' | 'unblock' | 'cut' }) {
  const isBacklog = /^BACKLOG-/.test(payload.itemId)
  if (payload.action === 'prioritize' || payload.action === 'unblock') {
    const item = findAndRemove(payload.itemId, [backlog.value, proposals.value])
    if (item) committed.value.push(item)
  } else {
    // deprioritize / cut: move back to its origin column (no persistence; demo only).
    const item = findAndRemove(payload.itemId, [backlog.value, proposals.value, committed.value])
    if (item) {
      if (isBacklog) backlog.value.push(item)
      else proposals.value.push(item)
    }
  }
}
</script>

<template>
  <header class="top">
    <h1>🗺️ Quarter Roadmap Co-Pilot <span style="color: var(--muted); font-weight: 400;">/ PromptJang</span></h1>
    <div class="meta" v-if="state">
      {{ state.quarter }} · <a href="/api/state">JSON</a> · <a href="/health">health</a>
    </div>
  </header>

  <main v-if="error">
    <div class="error">Failed to load: {{ error }}</div>
  </main>

  <main v-else-if="state">
    <CapacityBanner :capacity="state.capacity" :committed-hours="committedHours" />

    <section class="columns">
      <div class="column" id="backlog">
        <h2>Backlog (from past quarters)</h2>
        <div class="sub">Carried: in_progress / partially_done / blocked / not_started</div>
        <ItemCard
          v-for="item in backlog"
          :key="item.id"
          :item="item"
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

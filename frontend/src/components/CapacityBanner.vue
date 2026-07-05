<script setup lang="ts">
// The forcing-function banner. Tracks actual budget consumption: the "auto"
// items both agents already agreed on (baselineHours — always in scope, no
// button to un-commit them) plus whatever the human has committed so far from
// the decision-required items. Turns green once that total fits the budget.
//
// NOTE: this intentionally compares *used* hours (baseline + committed) against
// the budget directly — NOT "total demand minus committed" — because the
// latter inverts the signal (committing more would falsely look "more fit").
import { computed } from 'vue'
import type { CapacityEnvelope } from '../types'

const props = defineProps<{
  capacity: CapacityEnvelope
  committedHours: number
  baselineHours: number
}>()

const budget = computed(() => props.capacity.initiative_capacity_hours_q3 ?? 2400)
const usedHours = computed(() => props.baselineHours + props.committedHours)
const overBy = computed(() => usedHours.value - budget.value)
const isOver = computed(() => overBy.value > 0)
const pendingHours = computed(() => props.capacity.total_demand_hours - usedHours.value)
const barPct = computed(() => Math.min(100, Math.round((usedHours.value / budget.value) * 100)))
</script>

<template>
  <div class="banner static">
    <span>📋</span>
    <span>
      {{ capacity.delta_verdict }} — full ask <strong>{{ capacity.total_demand_hours }}h</strong>
      vs budget <strong>{{ budget }}h</strong> (+{{ capacity.delta_hours }}h over if everything ships).
    </span>
  </div>

  <div class="banner" :class="{ ok: !isOver }">
    <span>{{ isOver ? '⚠️' : '✅' }}</span>
    <div class="banner-body">
      <div>
        Live: <strong>{{ usedHours }}h</strong> used of <strong>{{ budget }}h</strong> budget
        ({{ baselineHours }}h auto-agreed + {{ committedHours }}h your decisions) →
        <span class="delta">
          {{ overBy > 0 ? '+' : '' }}{{ overBy }}h ({{ isOver ? 'still over — keep deciding' : 'fits' }})
        </span>
        <span v-if="pendingHours > 0" class="pending"> · {{ pendingHours }}h across the decision cards still undecided</span>
      </div>
      <div class="bar">
        <div class="bar-fill" :style="{ width: barPct + '%' }" />
      </div>
    </div>
  </div>
</template>

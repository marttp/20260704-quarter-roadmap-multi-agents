<script setup lang="ts">
// The forcing-function banner. Recomputes the running capacity delta from the
// current committed items. Turns green when the human has cut enough to fit.
import { computed } from 'vue'
import type { CapacityEnvelope } from '../types'

const props = defineProps<{
  capacity: CapacityEnvelope
  committedHours: number
}>()

const remaining = computed(() => props.capacity.total_demand_hours - props.committedHours)
const deltaAfter = computed(() => remaining.value - (props.capacity.initiative_capacity_hours_q3 ?? 2400))
const isOver = computed(() => deltaAfter.value > 0)
</script>

<template>
  <div class="banner" :class="{ ok: !isOver }">
    <span>{{ isOver ? '⚠️' : '✅' }}</span>
    <span>
      Committed so far <strong>{{ committedHours }}h</strong>; remaining demand
      <strong>{{ remaining }}h</strong> vs initiative budget
      <strong>{{ capacity.initiative_capacity_hours_q3 ?? 2400 }}h</strong> →
      <span class="delta">
        {{ deltaAfter > 0 ? '+' : '' }}{{ deltaAfter }}h ({{ isOver ? 'still over — cut more' : 'fits' }})
      </span>
    </span>
  </div>
</template>

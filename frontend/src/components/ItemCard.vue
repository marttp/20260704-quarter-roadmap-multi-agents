<script setup lang="ts">
// One roadmap item as a card. Emits `decide` with the chosen action when a
// button is clicked; the parent (App.vue) moves the card between columns.
import type { PlanningItem } from '../types'

const props = defineProps<{ item: PlanningItem }>()

const emit = defineEmits<{
  (e: 'decide', payload: { itemId: string; action: 'prioritize' | 'deprioritize' | 'unblock' | 'cut' }): void
}>()

function primaryAction(): 'prioritize' | 'deprioritize' | 'unblock' | 'cut' {
  return props.item.decision_type === 'unblock_vs_cut' ? 'unblock' : 'prioritize'
}

function secondaryAction(): 'prioritize' | 'deprioritize' | 'unblock' | 'cut' {
  return props.item.decision_type === 'unblock_vs_cut' ? 'cut' : 'deprioritize'
}
</script>

<template>
  <div class="card" :class="{ decision: item.decision_required }" :data-item-id="item.id">
    <div class="name">{{ item.name }}</div>

    <div class="meta-row">
      <span v-if="item.incoming_state" class="badge state">{{ item.incoming_state }}</span>
      <span
        v-if="item.decision_type && item.decision_type !== 'auto_keep' && item.decision_type !== 'auto_prioritize'"
        class="badge decision"
      >{{ item.decision_type }}</span>
      <span v-if="item.owner_team" class="badge team">{{ item.owner_team }}</span>
      <span v-if="item.effort_hours_remaining" class="badge team">{{ item.effort_hours_remaining }}h left</span>
    </div>

    <div v-if="item.origin" class="meta-row">origin: {{ item.origin }}</div>

    <div v-if="item.feedback.length" class="meta-row">
      <span
        v-for="(fb, i) in item.feedback"
        :key="i"
        class="badge"
        :class="fb.weight === 'high' ? 'decision' : 'team'"
      >{{ fb.source }} · {{ fb.weight }}</span>
    </div>

    <div v-if="item.blocker" class="meta-row" style="color: var(--danger);">⛔ blocked: {{ item.blocker }}</div>

    <div class="positions">
      <div class="position stakeholder">
        <div class="label">🟣 Stakeholder (Product): {{ item.stakeholder_position }}</div>
        <div class="reason">{{ item.stakeholder_reason }}</div>
      </div>
      <div class="position planning">
        <div class="label">🔵 Planning (Eng): {{ item.planning_position }}</div>
        <div class="reason">{{ item.planning_reason }}</div>
      </div>
    </div>

    <div v-if="item.decision_required" class="actions">
      <button class="primary" @click="emit('decide', { itemId: item.id, action: primaryAction() })">
        <template v-if="item.decision_type === 'unblock_vs_cut'">Unblock</template>
        <template v-else>↑ Prioritize</template>
      </button>
      <button class="danger" @click="emit('decide', { itemId: item.id, action: secondaryAction() })">
        <template v-if="item.decision_type === 'unblock_vs_cut'">Cut</template>
        <template v-else>↓ Deprioritize</template>
      </button>
    </div>
  </div>
</template>

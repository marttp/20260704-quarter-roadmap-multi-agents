<script setup lang="ts">
// Free-form chat with the advisor agent. Sends the user's question to /api/chat,
// which forwards to Agent Runtime where the classify_input_node routes it to
// the advisor_agent (free-form Q&A with data tools).
import { ref } from 'vue'

interface ChatMessage {
  role: 'user' | 'advisor' | 'system'
  text: string
}

const messages = ref<ChatMessage[]>([
  {
    role: 'system',
    text: 'Ask the advisor about team capacity, who to move between teams, or what to prioritize.',
  },
])
const input = ref('')
const loading = ref(false)

async function send() {
  const q = input.value.trim()
  if (!q || loading.value) return
  messages.value.push({ role: 'user', text: q })
  input.value = ''
  loading.value = true
  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: q }),
    })
    const data = await res.json()
    if (data.mode === 'live' && data.answer) {
      messages.value.push({ role: 'advisor', text: data.answer })
    } else if (data.mode === 'synthetic') {
      messages.value.push({ role: 'system', text: data.answer })
    } else if (data.mode === 'live_error') {
      messages.value.push({ role: 'system', text: `⚠️ ${data.error}` })
    } else {
      messages.value.push({ role: 'system', text: JSON.stringify(data).slice(0, 300) })
    }
  } catch (e) {
    messages.value.push({ role: 'system', text: `⚠️ ${e instanceof Error ? e.message : String(e)}` })
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="chat-panel">
    <h3>💬 Advisor Agent</h3>
    <div class="chat-messages">
      <div
        v-for="(m, i) in messages"
        :key="i"
        class="chat-msg"
        :class="m.role"
      >
        <span class="chat-author">{{ m.role === 'user' ? '🧑 You' : m.role === 'advisor' ? '🤖 Advisor' : '💡' }}</span>
        <div class="chat-text">{{ m.text }}</div>
      </div>
      <div v-if="loading" class="chat-msg system">
        <span class="chat-author">🤖 Advisor</span>
        <div class="chat-text">thinking…</div>
      </div>
    </div>
    <form @submit.prevent="send" class="chat-input-row">
      <input
        v-model="input"
        type="text"
        placeholder="e.g. Who can I move to Delivery to unblock Circuit Breakers?"
        :disabled="loading"
      />
      <button type="submit" :disabled="loading || !input.trim()">Send</button>
    </form>
  </section>
</template>

<script setup lang="ts">
// Free-form chat with the advisor agent. Sends the user's question to /api/chat,
// which forwards to Agent Runtime where the classify_input_node routes it to
// the advisor_agent (free-form Q&A with data tools).
import { nextTick, ref } from 'vue'

interface ChatMessage {
  role: 'user' | 'advisor' | 'system'
  text: string
}

// Current Q3 commit status, passed down from App.vue — sent with every
// question so the advisor reasons about what's actually already decided,
// not just the original static scenario (same gap /api/review had).
const props = defineProps<{
  alreadyCommitted: string[]
  committedHours: number
}>()

const WELCOME: ChatMessage = {
  role: 'system',
  text: 'Ask the advisor about team capacity, who to move between teams, or what to prioritize.',
}

const QUICK_PROMPTS = [
  'Who can I move to Delivery to unblock Circuit Breakers?',
  "What's over capacity right now?",
  'Which item should I cut first to fit the budget?',
]

const messages = ref<ChatMessage[]>([WELCOME])
const input = ref('')
const loading = ref(false)
const messagesEl = ref<HTMLDivElement | null>(null)

async function scrollToBottom() {
  await nextTick()
  if (messagesEl.value) {
    messagesEl.value.scrollTop = messagesEl.value.scrollHeight
  }
}

function clearChat() {
  messages.value = [WELCOME]
}

async function sendText(q: string) {
  if (!q || loading.value) return
  messages.value.push({ role: 'user', text: q })
  scrollToBottom()
  loading.value = true
  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question: q,
        already_committed: props.alreadyCommitted,
        committed_hours: props.committedHours,
      }),
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
    scrollToBottom()
  }
}

function send() {
  const q = input.value.trim()
  input.value = ''
  sendText(q)
}

function sendQuickPrompt(q: string) {
  sendText(q)
}
</script>

<template>
  <section class="chat-panel">
    <div class="chat-header">
      <h3>💬 Advisor Agent</h3>
      <button class="chat-clear" @click="clearChat" title="Clear the conversation">Clear</button>
    </div>

    <div class="chat-quick-prompts">
      <button
        v-for="(p, i) in QUICK_PROMPTS"
        :key="i"
        :disabled="loading"
        @click="sendQuickPrompt(p)"
      >{{ p }}</button>
    </div>

    <div class="chat-messages" ref="messagesEl">
      <div
        v-for="(m, i) in messages"
        :key="i"
        class="chat-msg"
        :class="m.role"
      >
        <span class="chat-author">{{ m.role === 'user' ? '🧑 You' : m.role === 'advisor' ? '🤖 Advisor' : '💡' }}</span>
        <div class="chat-text">{{ m.text }}</div>
      </div>
      <div v-if="loading" class="chat-msg advisor">
        <span class="chat-author">🤖 Advisor</span>
        <div class="chat-text typing-dots"><span /><span /><span /></div>
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

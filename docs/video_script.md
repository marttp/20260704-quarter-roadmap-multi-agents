# 5-Minute Video Script — Quarter Roadmap Co-Pilot (UPDATED for stable deploy)

**Length:** 5:00 hard cap. Single-take friendly.
**Required beats (rubric):** Problem Statement · Why Agents · Architecture · Demo · The Build.

**Before recording:** have both URLs open + verified:
- Dashboard: your Cloud Run URL (e.g. `https://quarter-roadmap-copilot-xxxx-uw.a.run.app`)
- Agent Runtime: confirmed via `curl -X POST <url>/api/chat -d '{"question":"hello"}'`

---

## 0:00–0:35 — Hook + Problem (title card or dashboard wide-shot)

> "Every quarter, a planning lead opens the spreadsheet and finds the same mess. Last quarter didn't finish cleanly — things shipped, things spilled over, something's blocked, something never started. Now we have to plan the next quarter on top of all that, with less capacity than we need.
>
> Today's tools *list* the mess. They don't *reason* across it. This project does — for a synthetic company called PromptJang, a webhook reliability platform."

**Title card:** *Quarter Roadmap Co-Pilot — two agents, one messy quarter, a human in the middle.*

---

## 0:35–1:15 — Why Agents, and Why Two

**Screen:** Antigravity IDE, `app/agent.py` open, scroll to show `planning_agent` + `stakeholder_agent` + `advisor_agent`.

> "One LLM could draft a prioritized list. But roadmap planning has real tension between departments. Product wants to ship; Engineering wants to protect utilization. One model playing both sides flattens that.
>
> So I built **three agents** with distinct mandates:
> - **Planning Agent** (Engineering) — cites utilization history, pushes back on over-commitment.
> - **Stakeholder Agent** (Product) — sees Eng's positions, argues for customer value.
> - **Advisor Agent** — answers free-form questions about the org: 'who can I move to another team?'"

---

## 1:15–2:00 — Architecture (30 seconds, keep it crisp)

**Screen:** `docs/architecture.md` — the Mermaid component graph + interaction sequence.

> "It's an ADK 2.0 graph Workflow. A classify node routes incoming messages: review requests go through the two-agent debate chain; questions go to the advisor. The dashboard is Vue 3 + TypeScript, the backend is FastAPI, the agent is deployed on Agent Runtime. The advisor has three MCP-style tools to read the org, utilization history, and initiatives."

Point at the graph as you say each component.

---

## 2:00–3:30 — LIVE DEMO: The Prioritization Board (core of the video)

**Screen:** Open the dashboard URL in browser. Zoom to 125%.

### Beat 1 — The board (0:20)
> "Here's Q3. The banner says demand exceeds the initiative budget by 260 hours. Four items are flagged for decision — each shows both agents' positions side by side."

**Point at:** Circuit Breakers card → 🟣 Stakeholder says *prioritize* (renewal risk) · 🔵 Planning says *deprioritize* (Delivery is on Signatures v2).

### Beat 2 — Make a decision (0:30)
> "Circuit Breakers has been cut twice already. The Stakeholder Agent argues a customer filed a reliability complaint. The Planning Agent argues the Delivery team can't absorb it alongside Signatures v2.
>
> I'll **deprioritize** — Planning's capacity argument wins this round."

**Click:** `↓ Deprioritize` on Circuit Breakers. Card animates.

### Beat 3 — Role-reversal beat (0:20)
> "Here's the interesting one — Ingestion tech debt. The roles **reverse**: Stakeholder wants to deprioritize (no customer voice); Planning insists (these footguns caused the Q1 over-commitment). I'll trust Eng and **prioritize**."

**Click:** `↑ Prioritize` on Ingestion debt. → Card moves to Q3 Committed.

### Beat 4 — Capacity turns green (0:20)
> "Watch the capacity banner — it's recomputing live as I commit and defer items."

**Show:** The banner updating with the running delta.

---

## 3:30–4:20 — LIVE DEMO: The Advisor Chat (the "wow" moment)

**Screen:** Scroll down to the 💬 Advisor Agent panel.

> "Now the part I'm most excited about. I can ask the advisor free-form questions about the organization — things a spreadsheet can't answer."

**Type in the chat box:**
> *"Who can I move to the Delivery team to help with Webhook Signatures v2?"*

**Hit Send.** Wait for the advisor's response (3–5 seconds).

**Read the response aloud** (it should name specific people by role + skills + capacity).

> "The advisor read the org data, checked each person's skills and team utilization, and recommended specific people — grounding the answer in the actual data, not hallucinating."

*(If time: ask a second question — "What should I deprioritize to fit the budget?" — to show the advisor reasoning about tradeoffs.)*

---

## 4:20–4:45 — Security + Deploy (25 seconds, show don't tell)

**Screen:** Terminal split — `curl` the health endpoint + the Cloud Run console.

> "On security: every payload runs through PII redaction before any agent sees it. Semgrep gates every commit.
>
> On deploy: the agent graph is on Agent Runtime, the dashboard is on Cloud Run. Both are live right now — this URL is the actual production endpoint."

**Show:** `curl <url>/health` → `{"agent_runtime_configured": true}`.

---

## 4:45–5:00 — Close

**Screen:** GitHub repo URL.

> "Built with Antigravity IDE and the Agents CLI through Kaggle's five-day course. Vue 3 + TypeScript frontend, FastAPI backend, ADK 2.0 multi-agent graph, local MCP server, all six capstone concepts covered. The repo's public — clone it and explore. Thanks for watching."

**End card:** repo URL + *capstone for the 5-Day AI Agents Intensive Vibe Coding Course with Google.*

---

## Recording tips

- [ ] Close Slack, email, notifications.
- [ ] Browser zoom 125% — text must be legible at 1080p.
- [ ] Have the dashboard pre-loaded + a chat response cached (so you know the agent answers successfully).
- [ ] If the advisor's response takes >5 seconds on camera, say "the advisor is reading the org data…" while waiting.
- [ ] Upload to YouTube as **unlisted**.
- [ ] Attach to the Kaggle Writeup Media Gallery + set a cover image (screenshot of the dashboard).

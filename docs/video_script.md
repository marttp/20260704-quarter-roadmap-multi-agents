# 5-Minute Video Script — Quarter Roadmap Co-Pilot

**Length:** 5:00 (hard cap per rubric). Single-take friendly — no editing required if you narrate steadily.
**Required beats (rubric):** Problem Statement · Why Agents · Architecture · Demo · The Build.

Record in Antigravity IDE so the build narrative is visible on screen (satisfies the Antigravity concept).

---

## 0:00–0:30 — Hook + Problem (no screen-share yet, or title card)

> "Every quarter, a planning lead opens the spreadsheet and finds the same mess. Last quarter didn't finish cleanly. A couple of things shipped. One's still in progress, spilling over. Something's partially done. One's blocked on another team. And one thing we planned — we never even started, because capacity evaporated.
>
> Now we have to plan the next quarter on top of all of that. Today's tools *list* the mess. They don't *reason* across it. This project does — for a synthetic company called PromptJang."

**Title card:** *Quarter Roadmap Co-Pilot — two agents, one messy quarter, a human in the middle.*

---

## 0:30–1:15 — Why Agents, and Why Two

**Screen:** Antigravity IDE showing `app/agent.py`.

> "I could ask one LLM to draft a prioritized list. But the real tension in roadmap planning is *between departments*. Product wants to ship for customers; Engineering wants to protect utilization. One model playing both sides flattens that into a polite compromise that hides the real disagreement.
>
> So I built two agents with opposed mandates. The Engineering Planning Agent emits first, citing the utilization history. The Product Stakeholder Agent responds having seen those positions. Where they disagree — the human decides."

Point at the workflow on screen as you say "two agents."

---

## 1:15–2:00 — Architecture

**Screen:** scroll `app/agent.py` slowly; or open `docs/architecture.md` to the Mermaid component graph.

> "It's an ADK 2.0 graph Workflow. Five nodes: load the planning state and redact PII; the Planning Agent emits structured positions; a small node combines context for the next agent; the Stakeholder Agent responds; a summarize node bundles both into a briefing with consensus and dispute counts. Both agents output through Pydantic schemas so the dashboard gets predictable JSON. Around the workflow: a local MCP server exposing the dataset, a Semgrep-plus-STRIDE security layer, and a Vue 3 dashboard."

---

## 2:00–3:30 — Live Demo (the core)

**Screen:** browser at `http://localhost:8080` (or the deployed Cloud Run URL).

> "Here's Q3. The banner says demand exceeds the initiative budget by 260 hours — so at least one decision has to go.
>
> Four items are flagged for decision. Let's take the first one — Circuit Breakers. Cut twice already. The Stakeholder Agent wants to prioritize it: a customer filed a reliability complaint, renewal is at risk. The Planning Agent wants to deprioritize: the Delivery team is fully committed to Webhook Signatures v2, stacking both would repeat our Q1 122% peak.
>
> I'll deprioritize it." *(click ↓ Deprioritize; card animates)*
>
> "Second one — Ingestion tech-debt remnant. This one's a role reversal. The Stakeholder wants to deprioritize: no customer voice, no revenue line. The Planning Agent insists: these two remaining footguns are exactly what caused the Q1 over-commitment, and we're about to add Regional Ingestion EU on top. I'll prioritize it." *(click ↑ Prioritize)*
>
> "Notice the capacity banner — it's recomputing live as I commit and defer items. Once I've cut enough it turns green, meaning the Q3 plan now fits the budget."

*(If you have time: click one more — the blocked API Keys item — to show the unblock-vs-cut decision type.)*

---

## 3:30–4:15 — Security + Deploy

**Screen:** terminal + browser.

> "On security — every payload runs through a `redact_confidential` function *before* any agent sees it, so employee names and the synthetic-data markers never reach the model. A Semgrep pre-commit gate scans for hardcoded API keys on every commit, and a STRIDE threat-modeling skill lives in the project for on-demand reviews.
>
> On deploy — the agent graph is on Agent Runtime, the FastAPI backend and Vue dashboard are on Cloud Run in a multi-stage container. The backend calls Agent Runtime's query endpoint to run the workflow."

*(Show the two URLs in browser tabs: the Cloud Run dashboard URL, and the Agent Runtime deployment in Cloud Console.)*

---

## 4:15–5:00 — The Build + Close

**Screen:** back to Antigravity IDE, or the GitHub repo.

> "Built with Antigravity IDE and the Agents CLI through Kaggle's five-day course — scaffold, lint, playground, deploy. A Vue 3 + TypeScript frontend, a FastAPI backend, a local MCP server, twenty-four tests, all six capstone concepts covered: ADK, MCP, Antigravity, Security, Deployability, Agent skills.
>
> The repo's public — clone it, run `make install && make frontend-build && make dashboard`, and you can explore all four decision items yourself. Thanks for watching."

**End card:** repo URL + *capstone for the 5-Day AI Agents Intensive Vibe Coding Course with Google.*

---

## Recording checklist

- [ ] Close notifications / Slack / email before recording.
- [ ] Increase browser zoom to 110–125% so text is legible at 1080p.
- [ ] Use a dark IDE theme (matches the dashboard).
- [ ] Have the dashboard pre-loaded with `make dashboard` running before you hit record.
- [ ] If you stumble, just pause and re-say the sentence — trim in editing, or leave the pause if single-taking.
- [ ] Upload to YouTube as **unlisted** (judges can view via the Writeup's Media Gallery; not publicly discoverable).
- [ ] Attach to the Kaggle Writeup Media Gallery + set a cover image.

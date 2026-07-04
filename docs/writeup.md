# Quarter Roadmap Co-Pilot

**Two agents, one messy quarter, a human in the middle.**

*An ADK 2.0 multi-agent system that helps a planner prioritize a quarterly roadmap when last quarter's work didn't finish neatly. A Product Stakeholder Agent and an Engineering Planning Agent debate each decision; the human makes the final call.*

**Track:** Agents for Business
**Course:** 5-Day AI Agents: Intensive Vibe Coding Course with Google
**Demo company:** PromptJang (synthetic — a webhook reliability & observability platform)

---

## 1. The problem

Real quarterly planning is messy. A quarter never finishes cleanly. By the time the next-quarter conversation starts, the previous quarter's commitments are scattered across a familiar set of states: a couple of items **shipped**, one or two **in-progress** and spilling over, something **partially done** with milestones split, at least one thing **blocked** on another team or vendor, and usually one initiative that was planned but **never began** because capacity evaporated.

The next-quarter conversation is then: *given all this half-done, stuck, and untouched work, plus the new things we want to build, plus what customers and the market are signalling, plus the engineering capacity we actually have — what do we do with each item?*

That synthesis — across **state × feedback × capacity** — is exactly the reasoning surface where a planning tool should help. Existing project-management tools list items; they don't *reason* across three forces and surface the decisions that genuinely need a human.

This project builds that reasoning layer for a synthetic but realistic mid-size company, **PromptJang** (a webhook reliability and observability platform). The dataset encodes one quarter of distant clean history (Q1), one just-ended quarter in a realistic mess (Q2), and a draft Q3 plan that over-runs the engineering initiative budget by 260 hours — forcing at least one prioritize-or-deprioritize decision.

## 2. Why agents, and why two

A single LLM call could draft a prioritized list. But the realistic tension in roadmap planning is **between departments with opposing mandates**: Product wants to maximize customer value and protect revenue commitments; Engineering wants to protect sustainable utilization. Forcing one model to play both sides flattens that tension into a polite compromise that pleases no one and hides the real disagreement.

So this project uses **two ADK LlmAgents with distinct mandates** that reason in sequence. The Engineering Planning Agent emits first, citing the Q1/Q2 utilization history (Ingestion peaked at 122% in week 8; two initiatives slipped to Q2) and the capacity envelope. The Product Stakeholder Agent responds *having seen* the Engineering position, citing customer feedback, market signals, and revenue risk. Where they disagree, the human decides.

That is honest multi-agent design. The agents embody the real organizational conflict instead of hiding it behind a single neutral voice. The disagreements are visible, traceable, and adjudicated by a human — which is exactly what a chief-of-staff should surface, not smooth over.

## 3. The scenario and the four decision beats

The Q3 planning input is shaped so the conversation is unavoidable. Four items are flagged `decision_required`, each exercising a different agent-reasoning path so the demo shows variety rather than volume:

- **Circuit Breakers** (carry-over, `not_started`) — cut twice already. *Prioritize vs deprioritize.* Stakeholder wants it (a customer filed a reliability complaint); Planning resists (the Delivery team is on Webhook Signatures v2).
- **Ingestion tech-debt remnant** (carry-over, `partially_done`) — internal, no customer voice. A deliberate **role-reversal beat**: here the Stakeholder resists and Planning insists, because those two remaining footguns are what compounded into the Q1 over-commitment.
- **API Keys & Permissions** (carry-over, `blocked` on Design) — a different decision type entirely: *unblock vs cut*. Stakeholder wants to pay the cost to unblock Design (security audit gap); Planning argues it's cheaper to cut and revisit with a simpler model in Q4.
- **Regional Ingestion EU** (new proposal) — *prioritize vs defer partial*. Stakeholder pushes for the full P0 revenue play; Planning proposes a scoped compromise (ship the EU endpoint only, defer the routing rules and Frankfurt point-of-presence to Q4).

Forcing all four decisions into a single 5-minute demo would be overwhelming; instead the video focuses on two of them to show the disagreement shape, and the dashboard exposes all four for the judge to explore.

## 4. Architecture

The system is an ADK 2.0 graph `Workflow` of five nodes:

```
START
  → load_planning_state_node   (reads the dataset, redacts PII, formats context)
  → planning_agent             (LlmAgent — Eng stance, structured AgentPositionsOutput)
  → build_stakeholder_input    (combines context + Eng positions for the next agent)
  → stakeholder_agent          (LlmAgent — Product stance, AgentPositionsOutput)
  → summarize_node             (combines into a PlanningBriefing with consensus/dispute counts)
  → END
```

The Planning Agent emits first; the Stakeholder Agent sees those positions before responding — a one-turn agent-to-agent exchange. Both outputs are structured through Pydantic `output_schema` so the dashboard receives predictable JSON, not free-form text. Every decision ends at a human Approve gate in the UI; nothing auto-commits.

Around the workflow sit four supporting surfaces:

- A **local MCP server** (FastMCP) exposes the synthetic dataset as MCP tools — `read_planning_state`, `read_utilization_history`, `read_initiatives`, `redact_text` — so any MCP-aware client (Antigravity, Agents CLI) can read the same source of truth the agents reason over.
- A **Security layer**: a `redact_confidential` function strips employee names and `(mock)` suffixes from every payload *before* any LlmAgent sees it; a Semgrep pre-commit gate scans for hardcoded API keys; a custom STRIDE threat-modeling skill lives in the project's `.agents/skills/`.
- A **Vue 3 + TypeScript dashboard** (Vite-built, served by FastAPI) renders the prioritization board with both agents' positions side-by-side per item, recomputes the running capacity delta live as the human commits or defers items, and turns the capacity banner green when enough has been cut to fit the budget.
- **Deploy targets**: the agent graph deploys to **Agent Runtime** (managed, stateful) via `agents-cli deploy`; the FastAPI + Vue SPA deploys to **Cloud Run** in a multi-stage container image. The Cloud Run backend calls Agent Runtime's `:query` REST endpoint to run the workflow.

## 5. The build journey

The project was vibe-coded following Kaggle's 5-Day AI Agents course. The workflow mirrors the public codelabs and uses **Google Antigravity** as the agentic IDE together with the **Agents CLI** for the agent lifecycle.

The agent graph itself was authored in Antigravity IDE against the **Agent Development Kit 2.0** graph Workflow API — the same pattern as the *Agent Lifecycle with Agents CLI + ADK 2.0* codelab. Iterating on the two agents' instructions and structured output schemas happened in the IDE's auxiliary pane, with the Agents CLI `playground` providing the interactive test loop and `lint` keeping the graph well-formed.

The **security-first** posture came from the *Secure Agentic Coding* codelab: a project-level `CONTEXT.md` codifies paved-road rules (Pydantic validation, no shell execution, a pre-commit remediation loop, mandatory PII redaction before any LLM call); a Semgrep rule with `--error` gates every commit; a custom STRIDE threat-modeling skill can be invoked on demand to produce a fresh `threat_model.md`. The `redact_confidential` function in `app/tools.py` is the visible artefact of that posture and is covered by six focused tests.

The **Vue 3 + TypeScript dashboard** replaces the original Jinja2 prototype, giving a component-based, fully typed UI that consumes a typed JSON contract mirroring the Pydantic schemas. The Vite dev server proxies `/api` to the FastAPI backend during development; production builds the SPA into the FastAPI static directory so the Cloud Run container serves both from one origin.

Deployment follows the *Deploy an ADK agent to Agent Runtime* and *Vibecode and Deploy a Frontend for an ADK agent* codelabs. The same `/api/review` endpoint returns `mode: "synthetic"` before the agent is deployed and `mode: "live"` once `AGENT_RUNTIME_ID` is set — so the dashboard works identically in local development and after the cloud deploy.

## 6. Concept coverage

The capstone requires at least three of the six key concepts. This project demonstrates all six:

| Key concept | Where it's demonstrated |
| --- | --- |
| Agent / Multi-agent system (ADK) | `app/agent.py` — `Workflow` with `planning_agent` + `stakeholder_agent` LlmAgents in a one-turn A2A exchange |
| MCP Server | `mcp_server/roadmap_mcp.py` — local FastMCP server exposing the dataset |
| Antigravity | Build narrative; the agent graph + dashboard were authored in Antigravity IDE |
| Security features | `redact_confidential` runs before any LLM call; Semgrep pre-commit gate; STRIDE skill; human Approve gate |
| Deployability | `agents-cli deploy` to Agent Runtime; multi-stage Dockerfile to Cloud Run; live public URL |
| Agent skills (Agents CLI) | `roadmap-conventions` + `stride-threat-model` skills; full `agents-cli` lifecycle (scaffold, lint, playground, deploy) |

## 7. The demo

The five-minute video (see `docs/video_script.md`) walks through: the problem; the architecture in Antigravity IDE; a live dashboard session where two of the four decision items are adjudicated; the capacity banner turning green once enough has been cut; the deployed Agent Runtime and Cloud Run URLs; and a short build-journey recap. The dashboard is fully interactive — judges can clone the repo, run `make install && make frontend-build && make dashboard`, and explore all four decision items themselves.

## 8. Limitations and future work

The dataset is **synthetic** and hand-curated to guarantee a compelling demo. Real adoption would replace it with a live integration — Jira, Asana, or Linear for initiatives; Looker or Hex for utilization history; a CRM for customer feedback signals. The MCP server's tool surface is the natural extension point for each.

The agent pair currently represents **two functions** (Product and Engineering). A larger org would add a Finance Agent (for revenue modelling on the P0 items) and a Design Agent (for the dependency conflict on UI-bound work). Each additional agent follows the same `LlmAgent` + `output_schema` pattern; the workflow graph extends linearly.

The two agents exchange positions in a **single turn**. A richer negotiation — multiple rounds where each agent revises its position in response to the other's evidence — would deepen the A2A story. The current one-turn design was chosen deliberately to keep the demo legible inside five minutes; multi-turn is a configuration change, not an architectural one.

Finally, the human-in-the-loop gate lives at the **decision layer** (the UI), not at an ADK `RequestInput` pause. This was a deliberate scope choice: the agents' job is to *advise*, the human's job is to *decide*, and the decision is naturally captured in the dashboard's Q3 Committed column. A future version could pause the workflow at `RequestInput` and persist decisions to the Agent Runtime Session Service for audit, but the current design already satisfies the human-oversight requirement.

## 9. Conclusion

Quarter roadmap planning is a genuinely good fit for an agentic system: the inputs are messy, the forces are genuinely in tension, and the synthesis is what humans actually spend hours doing. Building it as a two-agent system — with opposed mandates reasoning over shared evidence, surfacing their disagreement for a human to resolve — produces a more honest and more useful result than a single-agent draft. The capstone ships that system end-to-end: a typed multi-agent workflow, a local MCP surface, a security-first build posture, a Vue 3 dashboard, and a two-target cloud deploy.

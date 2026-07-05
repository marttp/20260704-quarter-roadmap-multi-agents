# Quarter Roadmap Co-Pilot

**Two agents, one messy quarter, a human in the middle.**

> An ADK 2.0 multi-agent system that helps a planner prioritize / deprioritize a quarterly roadmap when last quarter's work didn't finish neatly. A **Product Stakeholder Agent** and an **Engineering Planning Agent** debate each decision; the human makes the final call.

**Track:** Agents for Business
**Capstone:** 5-Day AI Agents Intensive Vibe Coding Course with Google (Kaggle, July 2026)
**Demo company:** PromptJang (synthetic data — webhook reliability & observability platform. All names `(mock)`.)

---

## 1. The problem

Real quarterly planning is messy. A quarter never finishes cleanly — items end up **in-progress**, **partially-done**, **blocked**, or **not-started**. The next-quarter conversation is then:

> *"Given all this half-done / stuck / untouched work + the new things we want + what customers and the market are signaling + the capacity we actually have — what do we do with each?"*

That synthesis — across **state × feedback × capacity** — is exactly the reasoning surface an agent is good at. Existing PM tools list items; they don't *reason* across three forces and surface the decisions that actually need a human.

## 2. Why agents (and why two)

A single LLM call could draft a prioritization. But the realistic tension in roadmap planning is **between departments with opposing mandates**: Product wants to maximize customer value; Engineering wants to protect sustainable utilization. Forcing one model to play both sides flattens that tension.

This project uses **two ADK LlmAgents with distinct mandates** that reason in sequence — the Eng Planning Agent emits first (citing the capacity + history evidence), then the Product Stakeholder Agent responds (citing customer/market feedback). Where they disagree, the human decides. That is honest multi-agent design: the agents embody the real organizational conflict instead of hiding it.

## 3. Architecture

```
START
  -> load_planning_state_node        (reads data/*.json, redacts PII, formats context)
  -> planning_agent                  (LlmAgent, Eng stance -> AgentPositionsOutput)
  -> build_stakeholder_input_node    (combines context + Eng positions)
  -> stakeholder_agent               (LlmAgent, Product stance -> AgentPositionsOutput)
  -> summarize_node                  (combines into PlanningBriefing for the UI)
  -> END
```

- **`planning_agent`** — Engineering Planning Agent. Mandate: protect ≤100% utilization. Cites Q1/Q2 history (Ingestion peaked at 122% in Q1) and the capacity envelope.
- **`stakeholder_agent`** — Product Stakeholder Agent ("the other department"). Mandate: maximize customer value + protect revenue. Cites customer / market / regulatory feedback.
- **`load_planning_state_node`** — deterministic loader that also runs `redact_confidential` **before** any LLM call (the Security feature).
- **`summarize_node`** — combines both agents' positions into a `PlanningBriefing` with consensus/dispute counts.

See **[app/data/README.md](app/data/README.md)** for the dataset, the four decision candidates, and the capacity envelope that forces a decision.

## 4. The build (Antigravity + Agents CLI)

This project was vibe-coded following Kaggle's 5-Day AI Agents course. The build workflow mirrors the public codelabs and uses **Google Antigravity** as the agentic IDE plus the **Agents CLI** for the agent lifecycle.

| Step | Tool | Codelab |
| --- | --- | --- |
| Author the ADK 2.0 graph + iterate on instructions | Antigravity IDE | [06 — Agent Lifecycle with Agents CLI + ADK 2.0](https://codelabs.developers.google.com/agents-cli-adk-lifecycle) |
| Install the toolchain + skills | `agents-cli` | [05 — Authoring Antigravity Skills](https://codelabs.developers.google.com/getting-started-with-antigravity-skills) |
| Security gate (Semgrep pre-commit + STRIDE skill) | Antigravity IDE | [08 — Secure Agentic Coding](https://codelabs.developers.google.com/secure-agentic-coding) |
| Deploy to Agent Runtime | `agents-cli deploy` | [10 — Deploy to Agent Runtime](https://codelabs.developers.google.com/enterprise-cloud-scale-deploying-the-expense-agent-to-agent-runtime-on-google-cloud) |

## 5. Quick start

### Prerequisites

- Python 3.11–3.13 (the project pins `>=3.11,<3.14`)
- [uv](https://docs.astral.sh/uv/) package manager
- Antigravity IDE (optional, for vibecoding edits) — [download](https://antigravity.google/download)
- A Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey)

### Install

```bash
# 1. Clone
git clone https://github.com/marttp/20260704-quarter-roadmap-multi-agents.git
cd 20260704-quarter-roadmap-multi-agents

# 2. Install dependencies (creates .venv automatically via uv)
uv sync --extra all

# 3. Install the Agents CLI toolchain + its companion skills globally
#    (one-time; adds skills to ~/.agents/skills/ discovered by Antigravity)
uvx google-agents-cli setup
agents-cli info   # verify

# 4. Set your Gemini API key (never commit this)
export GEMINI_API_KEY="your_key_here"
export GOOGLE_GENAI_USE_ENTERPRISE=FALSE

# 5. Build the Vue dashboard (one-time, then after each frontend change)
make frontend-install   # npm install in frontend/
make frontend-build     # Vite build -> submission_frontend/static/spa/
```

### Run

```bash
# Backend (FastAPI on :8080) — serves /api/state, /health, and the built Vue SPA
make dashboard

# OR: Vue dev server (:5173) with HMR + hot proxy to the backend on :8080
#     (run `make dashboard` in one terminal, `make frontend-dev` in another)
make frontend-dev

# Local ADK web playground (interactive) — codelab 06 pattern
agents-cli playground

# Single-shot CLI run
agents-cli run "Review the Q3 plan and surface the decision_required items."

# Lint + auto-fix
agents-cli lint
agents-cli lint --fix

# Tests
uv run pytest
```

## 6. Deploy to Agent Runtime (optional, recommended for the demo)

Deployment gives a public HTTPS endpoint — recommended for the capstone Deployability rubric item. Follows codelab 10.

```bash
# 0. Google Cloud prerequisites
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
gcloud services enable \
  aiplatform.googleapis.com \
  cloudtrace.googleapis.com \
  cloudbuild.googleapis.com \
  agentregistry.googleapis.com

# 1. Generate the production deployment descriptors (creates app/agent_runtime_app.py
#    + deployment_metadata.json; leaves app/agent.py untouched)
agents-cli scaffold enhance --deployment-target agent_runtime --yes

# 2. Lock deps + dry-run
uv lock
agents-cli deploy --dry-run

# 3. Deploy (5–10 minutes)
agents-cli deploy --project YOUR_PROJECT_ID --region us-west1
```

## 7. Concept coverage (capstone rubric: apply at least 3 of 6)

| Key concept | Where demonstrated | Status |
| --- | --- | --- |
| Agent / Multi-agent system (ADK) | `app/agent.py` — `Workflow` with `planning_agent` + `stakeholder_agent` LlmAgents, 1-turn A2A | ✅ |
| MCP Server | Local MCP server wrapping the synthetic PromptJang dataset (codelab 04 pattern) | ✅ |
| Antigravity | Build narrative + video recorded in Antigravity IDE | ✅ |
| Security features | `redact_confidential` runs before any LLM call; Semgrep pre-commit; STRIDE skill; human Approve gate | ✅ |
| Deployability | `agents-cli deploy` to Agent Runtime (codelab 10); live URL in the video | ✅ |
| Agent skills (Agents CLI) | `roadmap-conventions` skill + `agents-cli` lifecycle commands | ✅ |

## 8. Project structure

```
20260704-quarter-roadmap-multi-agents/
├── README.md                      # this file
├── data/                          # synthetic PromptJang dataset (see data/README.md)
│   ├── README.md
│   └── promptjang/{org,utilization,initiatives_q1,initiatives_q2,initiatives_q3,events}.json
├── app/
│   ├── agent.py                   # ADK 2.0 Workflow: load -> planning -> stakeholder -> summarize
│   ├── models.py                  # Pydantic schemas (agent I/O)
│   ├── tools.py                   # data loaders + redact_confidential
│   └── data/                      # synthetic PromptJang dataset (lives inside the package so it ships with the wheel)
│       ├── README.md
│       └── promptjang/{org,utilization,initiatives_q1,initiatives_q2,initiatives_q3,events}.json
├── frontend/                      # Vue 3 + Vite + TypeScript dashboard source
│   ├── src/
│   │   ├── App.vue                # three-column prioritization board
│   │   ├── api.ts                 # typed fetch client
│   │   ├── types.ts               # mirrors app/models.py
│   │   └── components/{ItemCard,CapacityBanner}.vue
│   ├── package.json
│   └── vite.config.ts             # dev proxy /api -> :8080; build -> submission_frontend/static/spa/
├── mcp_server/                    # local MCP wrapping the dataset (codelab 04 pattern)
├── .agents/                       # Antigravity customizations (codelab 08)
│   ├── CONTEXT.md                 # secure coding standards
│   ├── hooks.json                 # PreToolUse gate
│   ├── skills/                    # roadmap-conventions + stride-threat-model
│   └── scripts/validate_tool_call.py
├── .semgrep/rules.yaml            # static analysis (codelab 08)
├── .pre-commit-config.yaml        # Semgrep pre-commit gate (codelab 08)
├── submission_frontend/           # FastAPI JSON API + SPA host (codelab 09 pattern)
│   ├── main.py                    # /api/state, /health, serves built Vue SPA
│   └── static/spa/                # Vite build output (git-ignored)
├── tests/                         # pytest smoke tests (24)
├── docs/architecture.md           # Mermaid interaction + component diagrams
├── Makefile                       # install / playground / dashboard / frontend-* / deploy
├── pyproject.toml                 # deps: google-adk>=2.0.0a0, fastapi, pre-commit, semgrep, fastmcp, pytest
└── .env.example                   # GEMINI_API_KEY, GOOGLE_CLOUD_PROJECT, AGENT_RUNTIME_ID
```

## 9. Security

- **PII never reaches the model.** `redact_confidential` in `app/tools.py` strips employee names + `(mock)` suffixes from every payload before any `LlmAgent` invocation, even though the dataset is synthetic.
- **No auto-commit.** Every agent output ends at a human Approve gate in the dashboard; the system never finalizes a roadmap decision on its own.
- **Static-analysis gate.** `pre-commit` runs a custom Semgrep rule (`semgrep --error`) on every commit (codelab 08 pattern).
- **No secrets in code.** All credentials live in `.env` (git-ignored). `.env.example` ships placeholders only.

## 10. License

MIT — see [LICENSE](LICENSE). Dataset and code are synthetic/original; no real PromptJang customer, employee, or financial data is represented.

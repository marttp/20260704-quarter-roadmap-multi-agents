# Architecture & Interaction

Two views: the **component graph** (what runs where) and the **interaction sequence**
(what happens when the human clicks *Run Q3 review* then *Prioritize* on one item).

## 1. Component graph

```mermaid
flowchart LR
    classDef browser fill:#1f6feb22,stroke:#6ea8ff,color:#e6e9ef
    classDef api     fill:#4ade8022,stroke:#4ade80,color:#e6e9ef
    classDef agent   fill:#b08cff22,stroke:#b08cff,color:#e6e9ef
    classDef data    fill:#ffc85722,stroke:#ffc857,color:#e6e9ef

    subgraph Browser["Browser (user)"]
        UI["Vue 3 SPA<br/><i>frontend/</i>"]:::browser
    end

    subgraph CloudRun["Cloud Run"]
        API["FastAPI JSON API<br/><i>submission_frontend/main.py</i>"]:::api
    end

    subgraph AgentRuntime["Agent Runtime (managed)"]
        WF["ADK 2.0 Workflow<br/><i>app/agent.py</i>"]:::agent
        PA["Planning Agent<br/>(Eng stance)"]:::agent
        SA["Stakeholder Agent<br/>(Product stance)"]:::agent
    end

    subgraph Local["Local / sidecar"]
        MCP["MCP server<br/><i>mcp_server/roadmap_mcp.py</i>"]:::agent
        DATA[("Synthetic PromptJang<br/>dataset <i>data/</i>")]:::data
    end

    UI -- "GET /api/state<br/>POST /api/review" --> API
    API -- "invoke root workflow" --> WF
    WF -- "A2A (1-turn)<br/>sees Eng positions" --> SA
    WF -- "first emit<br/>(Eng stance)" --> PA
    WF -- "MCP tools<br/>read_planning_state" --> MCP
    MCP -- "loads" --> DATA
    WF -- "redact_confidential<br/>(PII scrub before LLM)" -.-> DATA
```

## 2. Interaction sequence — one full decision

```mermaid
sequenceDiagram
    autonumber
    actor U as Human (PM)
    participant UI as Vue 3 SPA
    participant API as FastAPI
    participant WF as ADK Workflow
    participant MCP as MCP server
    participant PA as Planning Agent
    participant SA as Stakeholder Agent

    Note over U,SA: Phase 1 — load + agent review
    U->>UI: opens dashboard
    UI->>API: GET /api/state
    API->>MCP: read_planning_state("Q3-2026")
    MCP-->>API: org + history + Q3 plan
    API-->>UI: 200 JSON (board renders)

    U->>UI: clicks "Run Q3 review"
    UI->>API: POST /api/review {quarter}
    API->>WF: invoke root_agent
    WF->>WF: load_planning_state_node + redact_confidential
    WF->>PA: AgentPositionsOutput (4 decision items)
    PA-->>WF: positions (Eng stance)
    WF->>SA: build_stakeholder_input_node + AgentPositionsOutput
    Note right of SA: sees PA's positions (A2A seam)
    SA-->>WF: positions (Product stance)
    WF->>WF: summarize_node (consensus vs dispute)
    WF-->>API: PlanningBriefing JSON
    API-->>UI: briefing
    UI-->>U: renders both positions per item

    Note over U,SA: Phase 2 — human decides one item
    U->>UI: clicks [Prioritize] on BACKLOG-01
    UI->>API: POST /api/decide {item_id, action}
    API->>WF: resume at human Approve gate
    WF-->>API: confirmed decision
    API-->>UI: updated Q3 Committed list
    UI-->>U: card animates into Q3 Committed column
```

## 3. The two agents' mandates (why they disagree)

```mermaid
graph LR
    subgraph Eng["Planning Agent (Engineering)"]
        EP["Mandate: protect ≤100% utilization"]
        EE["Evidence:<br/>- Q1 Ingestion peaked at 122%<br/>- 2 initiatives slipped to Q2<br/>- Q3 plan over budget by 260h"]
    end
    subgraph Prod["Stakeholder Agent (Product)"]
        PP["Mandate: maximize customer value"]
        PE["Evidence:<br/>- customer feedback signals<br/>- market/competitor moves<br/>- revenue commitments (P0/P1)"]
    end
    EP --> DEC{"decision_required item"}
    PP --> DEC
    DEC -->|consensus| KEEP[auto-commit]
    DEC -->|dispute| HUMAN["human Approve gate"]
```

## 4. Decision-candidate beats (the demo's variety)

The four `decision_required` items each exercise a different agent-reasoning path:

| Item | Incoming state | Decision type | Stakeholder | Planning |
| --- | --- | --- | --- | --- |
| BACKLOG-01 Circuit Breakers | `not_started` | prioritize vs deprioritize | prioritize (renewal) | deprioritize (capacity) |
| BACKLOG-02 Ingestion debt | `partially_done` | prioritize vs deprioritize *(role-reversal)* | deprioritize (no revenue) | prioritize (prevents Q1 repeat) |
| BACKLOG-03 API Keys | `blocked` | unblock vs cut | unblock (audit gap) | cut (cheaper to revisit) |
| Q3-ING-01 Regional EU | `not_started` | prioritize vs defer_partial | prioritize (P0 revenue) | defer_partial (capacity) |

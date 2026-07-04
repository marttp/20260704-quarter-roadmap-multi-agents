# Deploy Guide — Quarter Roadmap Co-Pilot

Two-target deploy on Google Cloud (codelab 09 + 10):
- **Agent Runtime** hosts the ADK 2.0 workflow.
- **Cloud Run** hosts the FastAPI backend + built Vue SPA.

The Cloud Run backend calls Agent Runtime's `:query` REST endpoint to run the
workflow (`POST /api/review`).

---

## 0. Before you start (accounts + credentials)

| What | Where | Notes |
| --- | --- | --- |
| Google Cloud project with **billing enabled** | [console.cloud.google.com](https://console.cloud.google.com) | Note the project ID. You must be `Owner` or `Editor` to deploy + grant IAM. |
| **Gemini API key** | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | Used for local `agents-cli playground` testing (codelab 06). Free tier is enough. |
| Google account with access to the project | — | `gcloud auth login` will open a browser. |

No service-account JSON keys. No Artifact Registry manual setup. Cloud Build
handles the container build when you run `gcloud run deploy --source .`.

---

## 1. Install / verify CLI tools on the home machine

```bash
# gcloud SDK — https://cloud.google.com/sdk/docs/install
gcloud --version           # verify

# uv (Python package manager) — https://docs.astral.sh/uv/
curl -LsSf https://astral.sh/uv/install.sh | sh
uv --version               # verify

# Agents CLI (codelab 06)
uvx google-agents-cli setup
agents-cli info            # verify; lists installed skills

# Node 22 + npm (for the Vue dashboard) — https://nodejs.org/
node --version && npm --version
```

---

## 2. Authenticate (refresh per session, ~30 seconds)

```bash
# User account login — opens browser.
gcloud auth login

# Application Default Credentials — what the /api/review endpoint uses to
# call Agent Runtime. Same browser flow.
gcloud auth application-default login

# Pin the project + region.
export GOOGLE_CLOUD_PROJECT=<your-project-id>
export GOOGLE_CLOUD_LOCATION=us-west1
gcloud config set project $GOOGLE_CLOUD_PROJECT
gcloud config set compute/region $GOOGLE_CLOUD_LOCATION
```

---

## 3. Enable the required APIs (one-time per project)

```bash
gcloud services enable \
  aiplatform.googleapis.com \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  agentregistry.googleapis.com \
  cloudtrace.googleapis.com
```

---

## 4. Clone + install (on the home machine)

```bash
git clone git@github.com:marttp/20260704-quarter-roadmap-multi-agents.git
cd 20260704-quarter-roadmap-multi-agents

# Python deps + pre-commit hook
make install                # uv sync --extra all + pre-commit install

# Build the Vue SPA (one-time, then after each frontend change)
make frontend-install       # npm install in frontend/
make frontend-build         # Vite build -> submission_frontend/static/spa/

# Sanity: tests + local dashboard
make test                   # 24 pytest tests, all green
make data-check             # validates data/promptjang/*.json
make dashboard              # FastAPI on :8080; open http://localhost:8080

# Optional: smoke-test the agent locally before deploying
export GEMINI_API_KEY=<your-key>
export GOOGLE_GENAI_USE_ENTERPRISE=FALSE
make playground             # agents-cli playground; verify the workflow runs
```

---

## 5. Deploy the agent to Agent Runtime (codelab 10)

```bash
# 5a. Generate the production deployment descriptors.
#     Creates app/agent_runtime_app.py + deployment_metadata.json.
make deploy-scaffold

# 5b. Lock deps + dry-run (catch config issues before paying for cloud).
make deploy-dry-run

# 5c. Deploy for real. 5-10 minutes.
make deploy-agent-runtime
# (Under the hood: agents-cli deploy --project $GOOGLE_CLOUD_PROJECT --region us-west1)

# The runtime id is captured in deployment_metadata.json. Verify:
cat deployment_metadata.json
```

---

## 6. Deploy the FastAPI + Vue SPA to Cloud Run (codelab 09)

```bash
# 6a. Build the Dockerfile on Cloud Build + deploy to Cloud Run.
#     The Makefile injects AGENT_RUNTIME_ID from deployment_metadata.json.
make deploy-cloud-run

# 6b. Grant the Cloud Run runtime SA roles/aiplatform.user so it can
#     :query Agent Runtime.
make deploy-iam
```

The deploy prints the public URL: `https://quarter-roadmap-copilot-<hash>-<region>.a.run.app`.

---

## 7. Verify the live deploy

```bash
DASHBOARD_URL=https://quarter-roadmap-copilot-<hash>-<region>.a.run.app

# Health — agent_runtime_configured should be true.
curl $DASHBOARD_URL/health

# Live agent run — mode should be "live" (not "synthetic").
curl -X POST $DASHBOARD_URL/api/review

# Open the dashboard in a browser and adjudicate a couple of decisions.
```

---

## 8. Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `make deploy-agent-runtime` → permission denied | User account lacks Editor/Owner | `gcloud projects add-iam-policy-binding $GOOGLE_CLOUD_PROJECT --member=user:YOU --role=roles/editor` |
| `/api/review` returns `mode: "synthetic"` post-deploy | `AGENT_RUNTIME_ID` not set on Cloud Run | Re-run `make deploy-cloud-run` (Makefile reads `deployment_metadata.json`); or `gcloud run services update quarter-roadmap-copilot --set-env-vars AGENT_RUNTIME_ID=...` |
| `/api/review` returns `mode: "live_error"` with 403 | Cloud Run SA lacks `roles/aiplatform.user` | Re-run `make deploy-iam` |
| `make deploy-cloud-run` fails on Cloud Build | Dockerfile error or quota | `gcloud builds log <build-id>` for details |
| Dashboard loads but `/` returns 503 "SPA not built" | `submission_frontend/static/spa/` missing in the image | Ensure `make frontend-build` ran locally; `.dockerignore` doesn't exclude it |
| `agents-cli` command not found | Toolchain not in PATH | Re-run `uvx google-agents-cli setup`; check `~/.local/bin` on PATH |

---

## 9. Cost notes (so there are no surprises)

- **Agent Runtime**: pay-per-use (requests + compute). A handful of demo calls costs cents.
- **Cloud Run**: pay-per-request; the default 0→1 autoscaling on `--allow-unauthenticated` is free-tier-friendly. Single demo instance is ~$0.
- **Cloud Build**: 120 free build-minutes/day.
- **After the capstone**: `gcloud run services delete quarter-roadmap-copilot` + delete the Agent Runtime engine from the Console to stop all charges.

---

## 10. One-shot deploy (after steps 1–4 are done)

```bash
make deploy-scaffold && \
make deploy-dry-run && \
make deploy-agent-runtime && \
make deploy-cloud-run && \
make deploy-iam && \
echo "✅ deployed — verify with: curl https://<url>/health"
```

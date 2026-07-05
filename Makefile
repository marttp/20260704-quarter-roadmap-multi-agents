# Quarter Roadmap Co-Pilot - Makefile.
# Each target maps to a codelab command. Run `make help` for the list.
# Requires: uv, agents-cli (installed via `uvx google-agents-cli setup`).

.PHONY: help install playground run lint test data-check dashboard \
        frontend-install frontend-build frontend-dev frontend-typecheck \
        deploy-scaffold deploy-dry-run deploy-agent-runtime deploy-cloud-run \
        deploy-iam clean

GOOGLE_CLOUD_PROJECT ?= your-gcp-project-id
GOOGLE_CLOUD_LOCATION ?= us-west1
DASHBOARD_PORT ?= 8080

help:
	@echo "Quarter Roadmap Co-Pilot - common targets:"
	@echo "  make install         - uv sync --extra all + pre-commit install"
	@echo "  make playground      - local ADK web playground (codelab 06)"
	@echo "  make run             - single-shot CLI run"
	@echo "  make dashboard       - FastAPI backend on :8080 (serves Vue SPA when built)"
	@echo "  make frontend-install- install Vue 3 dashboard deps"
	@echo "  make frontend-build  - build the Vue SPA into submission_frontend/static/spa/"
	@echo "  make frontend-dev    - Vite dev server on :5173 (HMR; proxies /api to :8080)"
	@echo "  make lint            - agents-cli lint + --fix"
	@echo "  make test            - pytest smoke tests"
	@echo "  make data-check      - validate data/promptjang/*.json"
	@echo "  make deploy-scaffold - generate Agent Runtime descriptors (codelab 10)"
	@echo "  make deploy-dry-run  - uv lock + agents-cli deploy --dry-run"
	@echo "  make deploy-agent-runtime - deploy ADK workflow to Agent Runtime (codelab 10)"
	@echo "  make deploy-cloud-run    - build + deploy FastAPI + Vue SPA to Cloud Run (codelab 09)"
	@echo "  make deploy-iam      - grant Cloud Run runtime SA roles/aiplatform.user"
	@echo "  make clean           - remove .venv + artifacts"

install:
	uv sync --extra all
	uv run pre-commit install

playground:
	agents-cli playground

dashboard:
	uv run uvicorn submission_frontend.main:app --port $(DASHBOARD_PORT) --reload

frontend-install:
	cd frontend && npm install

frontend-build:
	cd frontend && npm run build

frontend-dev:
	cd frontend && npm run dev

frontend-typecheck:
	cd frontend && npm run type-check

run:
	agents-cli run "Review the Q3 plan and surface the decision_required items with both agents' positions."

lint:
	agents-cli lint
	agents-cli lint --fix

test:
	uv run pytest

data-check:
	@uv run python -c "import json, pathlib; \
		files = list(pathlib.Path('data/promptjang').glob('*.json')); \
		[json.load(open(f)) for f in files]; \
		print(f'All {len(files)} data/promptjang/*.json files are valid JSON.')"

SERVICE_NAME ?= quarter-roadmap-copilot
# Short name (≤26 chars, lowercase) for agents-cli — the directory name
# (20260704-quarter-roadmap-multi-agents) exceeds agents-cli's 26-char limit.
AGENTS_CLI_NAME ?= quarter-roadmap-copilot

deploy-scaffold:
	agents-cli scaffold enhance --deployment-target agent_runtime --name $(AGENTS_CLI_NAME) --yes

deploy-dry-run:
	uv lock
	agents-cli deploy --dry-run

# Deploy the ADK workflow to Agent Runtime (codelab 10). Run deploy-scaffold first.
# Captures the runtime id in deployment_metadata.json.
deploy-agent-runtime:
	agents-cli deploy --project $(GOOGLE_CLOUD_PROJECT) --region $(GOOGLE_CLOUD_LOCATION)

# Deploy the FastAPI + Vue SPA to Cloud Run (codelab 09). Sets the env vars the
# backend needs to call Agent Runtime; --allow-unauthenticated makes the public URL.
# After this, run `make deploy-iam` so the runtime SA can invoke the agent.
SERVICE_NAME ?= quarter-roadmap-copilot
deploy-cloud-run:
	gcloud run deploy $(SERVICE_NAME) \
	  --source . --region $(GOOGLE_CLOUD_LOCATION) \
	  --allow-unauthenticated \
	  --set-env-vars GOOGLE_CLOUD_PROJECT=$(GOOGLE_CLOUD_PROJECT),GOOGLE_CLOUD_LOCATION=$(GOOGLE_CLOUD_LOCATION),AGENT_RUNTIME_ID=$$(test -f deployment_metadata.json && python3 -c "import json,sys;print(json.load(open('deployment_metadata.json')).get('agent_runtime_id',''))") \
	  --quiet

# Grant the Cloud Run runtime SA roles/aiplatform.user so it can :query Agent Runtime.
deploy-iam:
	@RUNNER_SA=$(GOOGLE_CLOUD_PROJECT)-compute@developer.gserviceaccount.com; \
	gcloud projects add-iam-policy-binding $(GOOGLE_CLOUD_PROJECT) \
	  --member="serviceAccount:$$RUNNER_SA" \
	  --role="roles/aiplatform.user" --quiet

clean:
	rm -rf .venv artifacts

# Quarter Roadmap Co-Pilot - Makefile.
# Each target maps to a codelab command. Run `make help` for the list.
# Requires: uv, agents-cli (installed via `uvx google-agents-cli setup`).

.PHONY: help install playground run lint test data-check dashboard \
        deploy-scaffold deploy-dry-run deploy clean

GOOGLE_CLOUD_PROJECT ?= your-gcp-project-id
GOOGLE_CLOUD_LOCATION ?= us-west1
DASHBOARD_PORT ?= 8080

help:
	@echo "Quarter Roadmap Co-Pilot - common targets:"
	@echo "  make install         - uv sync --extra all + pre-commit install"
	@echo "  make playground      - local ADK web playground (codelab 06)"
	@echo "  make run             - single-shot CLI run"
	@echo "  make dashboard       - FastAPI prioritization dashboard (codelab 09)"
	@echo "  make lint            - agents-cli lint + --fix"
	@echo "  make test            - pytest smoke tests"
	@echo "  make data-check      - validate data/promptjang/*.json"
	@echo "  make deploy-scaffold - generate Agent Runtime descriptors (codelab 10)"
	@echo "  make deploy-dry-run  - uv lock + agents-cli deploy --dry-run"
	@echo "  make deploy          - agents-cli deploy (set GOOGLE_CLOUD_PROJECT)"
	@echo "  make clean           - remove .venv + artifacts"

install:
	uv sync --extra all
	uv run pre-commit install

playground:
	agents-cli playground

dashboard:
	uv run uvicorn submission_frontend.main:app --port $(DASHBOARD_PORT) --reload

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

deploy-scaffold:
	agents-cli scaffold enhance --deployment-target agent_runtime --yes

deploy-dry-run:
	uv lock
	agents-cli deploy --dry-run

deploy:
	agents-cli deploy --project $(GOOGLE_CLOUD_PROJECT) --region $(GOOGLE_CLOUD_LOCATION)

clean:
	rm -rf .venv artifacts

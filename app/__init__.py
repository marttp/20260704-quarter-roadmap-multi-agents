"""Quarter Roadmap Co-Pilot — app package.

Re-exports `app` (the ADK App instance) so both discovery paths work:
  - `from app.agent import app`   (used in app/agent.py's own module)
  - `from app import app`         (used by agents-cli playground / external tooling)

Per agents-cli scaffold convention.
"""

from app.agent import app  # noqa: F401  (re-exported for tooling discovery)

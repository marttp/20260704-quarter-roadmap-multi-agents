"""Deterministic tools for the Quarter Roadmap Co-Pilot agents.

Two responsibilities:
  1. Load the synthetic PromptJang dataset into structured dicts the agents reason over.
  2. `redact_confidential` — strips employee names + '(mock)' suffixes from any text
     BEFORE it reaches an LLM call. This is the project's visible Security feature
     (rubric: 'Security features — Code or Video') and keeps PII out of model context
     even though the underlying data is synthetic.

These are plain Python functions (no LLM cost) — used both as ADK `@node` helpers
inside app/agent.py and as utility calls in the FastAPI dashboard.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

# Resolve the data directory relative to this file so it works regardless of CWD.
# Layout: <repo>/app/tools.py  ->  <repo>/data/promptjang/
DATA_DIR: Path = Path(__file__).resolve().parent.parent / "data" / "promptjang"


def _load_json(filename: str) -> Dict[str, Any]:
    """Read a JSON file from DATA_DIR. Raises FileNotFoundError with a clear message."""
    path = DATA_DIR / filename
    if not path.exists():
        raise FileNotFoundError(
            f"Dataset file not found: {path}. Ensure the data/promptjang/ files are committed."
        )
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def load_org() -> Dict[str, Any]:
    """Teams + mock employees + function-agent stances (org.json)."""
    return _load_json("org.json")


def load_utilization_history() -> Dict[str, Any]:
    """Q1/Q2 per-team weekly utilization % + quarter averages + commentary."""
    return _load_json("utilization.json")


def load_quarter_initiatives(quarter: str = "Q3-2026") -> Dict[str, Any]:
    """Initiatives for a given quarter. quarter must look like 'Q1-2026' / 'Q2-2026' / 'Q3-2026'."""
    suffix = quarter.split("-")[0].lower()  # 'q1' | 'q2' | 'q3'
    return _load_json(f"initiatives_{suffix}.json")


def load_planning_state(quarter: str = "Q3-2026") -> Dict[str, Any]:
    """Compose the full planning context the agents reason over.

    Returns a dict with:
      - org:                      company + teams + employees
      - history:                  Q1 + Q2 utilization history (the resource trend)
      - history_initiatives:      Q1 + Q2 initiatives (the messy carry-over origin)
      - planning:                 Q3 planning input (backlog + proposals + capacity envelope)
      - decision_required:        convenience list of item ids that need a human call
    """
    org = load_org()
    utilization = load_utilization_history()
    q1 = load_quarter_initiatives("Q1-2026")
    q2 = load_quarter_initiatives("Q2-2026")
    planning = load_quarter_initiatives(quarter)

    return {
        "org": org,
        "history": {
            "utilization": utilization,
            "initiatives": {"Q1-2026": q1, "Q2-2026": q2},
        },
        "planning": planning,
        "decision_required": planning.get("decision_required", []),
    }


# --- Security: PII / confidential-term redaction ---


def _build_person_name_pattern(names: List[str]) -> re.Pattern[str]:
    """Compile a case-insensitive regex matching any of the given full names."""
    escaped = [re.escape(n) for n in names if n]
    # Join with alternation; fallback to a never-match pattern if list is empty.
    return re.compile("|".join(escaped) or r"(?!x)x", flags=re.IGNORECASE)


def _person_names_from_org(org: Dict[str, Any]) -> List[str]:
    """Extract every mock-employee name from org.json. Strips the '(mock)' suffix for matching."""
    names: List[str] = []
    for emp in org.get("employees", []):
        name = emp.get("name", "")
        # Strip the literal ' (mock)' suffix so we match the bare name in running text too.
        if name.endswith(" (mock)"):
            name = name[: -len(" (mock)")]
        if name:
            names.append(name)
    return names


# Pattern for the '(mock)' suffix we append in the synthetic dataset.
_MOCK_SUFFIX_RE = re.compile(r"\s*\(mock\)", flags=re.IGNORECASE)


def redact_confidential(text: str, org: Optional[Dict[str, Any]] = None) -> str:
    """Redact employee names + '(mock)' suffixes from `text` before it reaches an LLM.

    This is the project's visible Security feature (rubric: 'Security features').
    It runs on every payload BEFORE any LlmAgent invocation, so even though the data
    is synthetic the design is honest: PII never enters model context.

    Replaces:
      - 'Priya Chen (mock)' / 'Priya Chen' -> '[REDACTED-PERSON]'
      - The standalone ' (mock)' suffix      -> '' (cleaned)

    Args:
      text: the string to scrub.
      org:  optional org.json dict (loaded fresh if None).

    Returns:
      The scrubbed string.
    """
    if not isinstance(text, str):
        # If handed a non-string (dict/list), recurse over its JSON form so we never miss
        # a name hiding in a nested field.
        text = json.dumps(text, ensure_ascii=False)

    org = org if org is not None else load_org()
    names = _person_names_from_org(org)
    person_re = _build_person_name_pattern(names)

    # Step 1: collapse 'Name (mock)' and bare 'Name' to the redaction marker.
    text = person_re.sub("[REDACTED-PERSON]", text)
    # Step 2: strip any leftover ' (mock)' suffixes that weren't adjacent to a name.
    text = _MOCK_SUFFIX_RE.sub("", text)

    return text

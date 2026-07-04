# Local Project Context & Secure Coding Standards
# Adapted from codelab 08 (https://codelabs.developers.google.com/secure-agentic-coding)
# for the Quarter Roadmap Co-Pilot.

## Core Paved Roads
We systematically address common vulnerability classes by guiding the agent
to use our pre-configured, secure-by-default helper patterns instead of
writing raw implementation logic from scratch.

1. **Tool Input Validation**: Every agent tool must validate incoming
   parameters against strict Pydantic schemas rather than parsing raw
   dictionaries or strings. (See `app/models.py` for the project schemas.)
2. **No Shell Execution**: Never use `run_command` or raw shell execution
   tools unless explicitly approved by `hooks.json`.
3. **Pre-Commit Remediation Loop**: If a git commit fails due to a pre-commit
   hook error (such as a Semgrep scan finding), you MUST treat the violation
   as a refactoring task, apply targeted fixes, run tests to verify no
   regressions, and attempt to commit again.
4. **PII Redaction Before LLM Calls** *(project-specific)*: Every payload that
   reaches a `LlmAgent` must first pass through `app.tools.redact_confidential`.
   Employee names + `(mock)` suffixes must never enter model context. This is
   the project's visible Security feature (rubric: 'Security features').

## TDD Planning Gate
During the Plan phase, you must decompose the workspace task into logical,
modular stages. Every implementation plan MUST include a dedicated
**Security Boundaries & Assertions** section outlining specific edge cases
that could exploit the feature.

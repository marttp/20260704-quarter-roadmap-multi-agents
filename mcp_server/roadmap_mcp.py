"""Local MCP server exposing the synthetic PromptJang dataset as MCP tools.

This is the project's MCP surface (rubric: 'MCP Server — Code'). Antigravity,
Agents CLI, or any MCP-aware client can connect to it and read the planning
state / history without coupling to the app package directly.

Run (stdio transport — the default for local MCP):
    uv run python -m mcp_server.roadmap_mcp

Connect from Antigravity by adding this to ~/.gemini/config/mcp_config.json
(codelab 04 pattern):
    {
      "mcpServers": {
        "roadmap-mcp": {
          "command": "uv",
          "args": ["run", "--directory", "<abs-path-to-this-repo>",
                   "python", "-m", "mcp_server.roadmap_mcp"]
        }
      }
    }
"""

from __future__ import annotations

from typing import Dict, Any

from fastmcp import FastMCP  # type: ignore

from app.tools import (
    load_org,
    load_planning_state,
    load_quarter_initiatives,
    load_utilization_history,
    redact_confidential,
)

# The server's tool name shows up in MCP clients (Antigravity's /mcp list).
mcp = FastMCP("roadmap-mcp")


@mcp.tool()
def read_planning_state(quarter: str = "Q3-2026") -> Dict[str, Any]:
    """Return the full planning state: org, Q1/Q2 history, Q3 plan, decision_required ids.

    Use this first to load everything the agents reason over.
    """
    return load_planning_state(quarter)


@mcp.tool()
def read_utilization_history() -> Dict[str, Any]:
    """Return the Q1/Q2 per-team weekly utilization % + quarter averages + commentary."""
    return load_utilization_history()


@mcp.tool()
def read_initiatives(quarter: str = "Q3-2026") -> Dict[str, Any]:
    """Return the initiatives for one quarter ('Q1-2026', 'Q2-2026', or 'Q3-2026')."""
    return load_quarter_initiatives(quarter)


@mcp.tool()
def read_org() -> Dict[str, Any]:
    """Return teams + mock employees + function-agent stances."""
    return load_org()


@mcp.tool()
def redact_text(text: str) -> str:
    """Redact employee names + '(mock)' suffixes from `text` (the Security feature, exposed over MCP)."""
    return redact_confidential(text)


if __name__ == "__main__":
    # stdio transport — what local MCP clients (Antigravity, Agents CLI) expect.
    mcp.run()

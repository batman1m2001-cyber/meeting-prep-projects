"""The CRM and the calendar, served as MCP tools.

    uv run prep-mcp          stdio (an MCP client starts it as a subprocess)

Any MCP client lists these tools and calls them — the agent never sees SQL.
"""
from __future__ import annotations

try:                                   # mcp 2.x
    from mcp.server.mcpserver import MCPServer
except ImportError:                    # mcp 1.x (langchain-mcp-adapters still pins it)
    from mcp.server.fastmcp import FastMCP as MCPServer

from prep_world import db

mcp = MCPServer("crm-calendar")


@mcp.tool()
def crm_find_company(domain_or_name: str) -> dict:
    """Find a company in the CRM by its email domain or name. Returns its profile, or {} if unknown."""
    return db.find_company(domain_or_name) or {}


@mcp.tool()
def crm_contacts(company_id: str) -> list[dict]:
    """The people we know at a company: name, title, email."""
    return db.contacts(company_id)


@mcp.tool()
def crm_history(company_id: str) -> list[dict]:
    """Our past interactions with a company (pilots, calls, events), oldest first."""
    return db.history(company_id)


@mcp.tool()
def calendar_meetings(company_id: str) -> list[dict]:
    """Upcoming meetings with a company: when, title, attendees."""
    return db.meetings(company_id)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()

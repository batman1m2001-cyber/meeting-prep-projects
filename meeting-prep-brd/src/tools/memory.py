"""memory: what the assistant remembers between runs — facts and results per
company or user, the research history, and the user's profile."""
from __future__ import annotations

from stores import brd

from tools._server import MCPServer, ToolError

server = MCPServer("memory")
KINDS = ("fact", "result", "research")


@server.tool()
def recall(subject: str, query: str | None = None, k: int = 10) -> list[dict]:
    """What is remembered about a subject (a company id, or "user:<id>"): nearest to `query`, else newest first."""
    return brd.recall(subject, query, k)


@server.tool()
def remember(subject: str, kind: str, content: str, source: str | None = None) -> dict:
    """Remember one item about a subject. kind: fact | result | research (a research run: also added to history)."""
    if kind not in KINDS:
        raise ToolError(f"kind must be one of {KINDS}, got {kind!r}")
    stored = brd.remember(subject, kind, content, source)
    if kind == "research":
        stored["run_id"] = brd.add_research_run(subject, None, content, [source] if source else [])
    return stored


@server.tool()
def history(company_id: str) -> list[dict]:
    """Past research runs on a company, newest first: summary, sources, when."""
    return brd.research_runs(company_id)


@server.tool()
def user_profile(user_id: str = "sales") -> dict:
    """Who the brief is for and how they want it (format, language, focus)."""
    return brd.user_profile(user_id) or {}


def main() -> None:
    server.run()


if __name__ == "__main__":
    main()

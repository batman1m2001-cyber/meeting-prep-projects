"""kb: the knowledge base — CRM notes and every approved brief, searched by meaning."""
from __future__ import annotations

from stores import brd

from tools._server import MCPServer

server = MCPServer("kb")


@server.tool()
def search(query: str, company_id: str | None = None, k: int = 3) -> list[dict]:
    """The `k` notes nearest to `query`, optionally only one company's: company_id, source, content, distance."""
    return brd.kb_search(query, company_id, k)


@server.tool()
def save(company_id: str, source: str, content: str) -> dict:
    """Save a document (e.g. an approved brief) into the knowledge base."""
    return {"id": brd.kb_save(company_id, source, content)}


def main() -> None:
    server.run()


if __name__ == "__main__":
    main()

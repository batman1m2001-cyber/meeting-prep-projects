"""crm: companies, the people we know there, and our history with them (read-only)."""
from __future__ import annotations

from prep_world import db

from tools._server import MCPServer

server = MCPServer("crm")


@server.tool()
def find_company(domain_or_name: str) -> dict:
    """A company by its email domain, name or id: its profile, or {} when the CRM does not know it."""
    return db.find_company(domain_or_name) or {}


@server.tool()
def contacts(company_id: str) -> list[dict]:
    """The people we know at a company: name, title, email."""
    return db.contacts(company_id)


@server.tool()
def history(company_id: str) -> list[dict]:
    """Our past interactions with a company (pilots, calls, events), oldest first."""
    return db.history(company_id)


def main() -> None:
    server.run()


if __name__ == "__main__":
    main()

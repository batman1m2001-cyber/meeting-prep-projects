"""calendar: the work calendar (read-only). "Today" is the world's demo day."""
from __future__ import annotations

from prep_world import db, world

from tools._server import MCPServer

server = MCPServer("calendar")


@server.tool()
def meetings(company_id: str) -> list[dict]:
    """Meetings booked with a company: starts_at, title, attendees."""
    return db.meetings(company_id)


@server.tool()
def upcoming(days: int) -> list[dict]:
    """Every meeting in the next `days` days, soonest first: company_id, starts_at, title, attendees."""
    return db.rows("SELECT company_id, starts_at::text, title, attendees FROM meetings "
                   "WHERE starts_at >= %s::date AND starts_at < %s::date + %s ORDER BY starts_at",
                   world()["today"], world()["today"], days)


def main() -> None:
    server.run()


if __name__ == "__main__":
    main()

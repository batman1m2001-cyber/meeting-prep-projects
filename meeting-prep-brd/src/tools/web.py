"""web: search, read a page, recent news. Pages come back as a person sees them:
hidden text and instruction-shaped lines are dropped (`prep_world.guard`)."""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import date

from prep_world import WEB, world
from prep_world.guard import visible_text

from tools._server import MCPServer, ToolError

server = MCPServer("web")


def _get(path: str) -> str:
    with urllib.request.urlopen(WEB + path, timeout=15) as r:
        return r.read().decode("utf-8", "replace")


@server.tool()
def search(query: str, n: int = 5) -> list[dict]:
    """Web search: title, url, snippet, date (news has a date)."""
    return json.loads(_get(f"/search?{urllib.parse.urlencode({'q': query, 'n': min(n, 20)})}"))


@server.tool()
def fetch(url: str) -> dict:
    """Read one web page as text: url, text."""
    if not url.startswith(WEB + "/web/"):
        raise ToolError(f"only pages under {WEB}/web/ can be read")
    return {"url": url, "text": visible_text(_get(url[len(WEB):]))}


@server.tool()
def news(company: str, domain: str, days: int = 30) -> list[dict]:
    """News published on a company's own site (`domain`), newest first:
    title, date, url, snippet, age_days, fresh (within `days`)."""
    today = date.fromisoformat(world()["today"])
    own = f"{WEB}/web/{domain}/"
    out = []
    for hit in search(f"{company} {domain}", n=20):
        if hit.get("date") and hit["url"].startswith(own):
            age = (today - date.fromisoformat(hit["date"])).days
            out.append({**hit, "age_days": age, "fresh": age <= days})
    return sorted(out, key=lambda h: h["date"], reverse=True)


def main() -> None:
    server.run()


if __name__ == "__main__":
    main()

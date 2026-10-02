"""report: a brief in Markdown, and as an email body."""
from __future__ import annotations

import re

from stores import brd

from tools._server import MCPServer, ToolError

server = MCPServer("report")
SECTIONS = ("Introduction", "Field", "Products", "Recent news", "Contacts", "Points to note")


def _bullets(text: str) -> str:
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    return "\n".join(ln if ln.startswith(("-", "*")) else f"- {ln}" for ln in lines) or "- (none found)"


@server.tool()
def render_markdown(company_id: str, title: str, introduction: str, field: str, products: str,
                    recent_news: str, contacts: str, points_to_note: str) -> dict:
    """Render the brief's six sections (one item per line) as Markdown and store it: report_id, markdown."""
    parts = (introduction, field, products, recent_news, contacts, points_to_note)
    markdown = f"# {title}\n\n" + "\n\n".join(f"## {h}\n{_bullets(p)}" for h, p in zip(SECTIONS, parts)) + "\n"
    return {"report_id": brd.save_report(company_id, title, markdown), "markdown": markdown}


@server.tool()
def email_body(report_id: int) -> dict:
    """A stored report as a plain-text email: report_id, subject, body."""
    r = brd.report(report_id)
    if r is None:
        raise ToolError(f"no report {report_id}")
    body = re.sub(r"^#+\s*", "", r["markdown"], flags=re.M)
    body = re.sub(r"\*\*(.+?)\*\*", r"\1", body)
    brd.set_email_body(report_id, body)
    return {"report_id": report_id, "subject": f"Brief: {r['title']}", "body": body}


def main() -> None:
    server.run()


if __name__ == "__main__":
    main()

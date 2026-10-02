"""mail: the sales inbox (Mailpit) and outgoing mail (SMTP).

An id `golden:<id>` reads a golden email from the world instead of the inbox,
so the eval runs the same Email Agent without a mail server.
"""
from __future__ import annotations

import json
import smtplib
import urllib.parse
import urllib.request
from email.message import EmailMessage
from email.utils import make_msgid

from prep_world import MAIL_API, SMTP, golden, mail, world

from tools._server import MCPServer

server = MCPServer("mail")
GOLDEN = "golden:"


def _api(path: str) -> dict:
    with urllib.request.urlopen(MAIL_API + path, timeout=10) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


@server.tool()
def list_new() -> list[dict]:
    """Unread emails in the sales inbox, oldest first: id, from, subject, date."""
    return mail.list_new()


@server.tool()
def read(email_id: str) -> dict:
    """One email: id, from, from_name, to, subject, text, attachments [{name, text}]."""
    if email_id.startswith(GOLDEN):
        g = next((e for e in golden() if e["id"] == email_id[len(GOLDEN):]), None)
        if g is None:
            raise ValueError(f"no email {email_id!r}")
        return {**mail.as_email(g), "id": email_id}
    return mail.read(email_id)


@server.tool()
def send(to: str, subject: str, body: str, approval_id: int) -> dict:
    """Send an email. `approval_id` is the approved request this send carries out."""
    msg = EmailMessage()
    msg["From"] = f"Meeting Prep <prep@{world()['us']['domain']}>"
    msg["To"] = to
    msg["Subject"] = subject
    msg["Message-ID"] = make_msgid(domain=world()["us"]["domain"])
    msg["X-Approval-Id"] = str(approval_id)
    msg.set_content(body)
    host, port = SMTP.split(":")
    with smtplib.SMTP(host, int(port), timeout=10) as s:
        s.send_message(msg)
    return {"message_id": msg["Message-ID"].strip("<>"), "status": "sent"}


@server.tool()
def status(message_id: str) -> dict:
    """Where a sent email is: delivered (in the mail server, with its server id) or unknown."""
    q = urllib.parse.quote(f"message-id:{message_id}")
    hits = _api(f"/api/v1/search?query={q}").get("messages") or []
    if not hits:
        return {"message_id": message_id, "status": "unknown"}
    return {"message_id": message_id, "status": "delivered", "server_id": hits[0]["ID"]}


def main() -> None:
    server.run()


if __name__ == "__main__":
    main()

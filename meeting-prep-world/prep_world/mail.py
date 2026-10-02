"""The inbox: Mailpit behind three calls, so a Gmail adapter would be one file.

    list_new()                 unread emails, oldest first: [{id, from, subject, date}]
    read(id)                   one email: {id, from, from_name, to, subject, text, attachments: [{name, text}]}
    send(to, subject, body)    send over SMTP
    mark_read(id)
    as_email(golden)           a golden email in read()'s shape
    golden_cases()             the golden emails as eval cases

    uv run prep-send lotus-intro     send a golden email "as the customer" (the demo trigger)
    uv run prep-send --list          the golden email ids
"""
from __future__ import annotations

import json
import smtplib
import sys
import urllib.request
from email.message import EmailMessage
from email.utils import parseaddr

from prep_world import MAIL_API, SMTP, golden, world


def _api(path: str, method: str = "GET", body: dict | None = None) -> dict | list | str:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(MAIL_API + path, data, {"content-type": "application/json"}, method=method)
    with urllib.request.urlopen(req, timeout=10) as r:
        raw = r.read().decode("utf-8", "replace")
    try:
        return json.loads(raw)
    except ValueError:
        return raw


def list_new() -> list[dict]:
    msgs = _api("/api/v1/messages?limit=200")["messages"]
    return [{"id": m["ID"], "from": m["From"]["Address"], "subject": m["Subject"], "date": m["Created"]}
            for m in reversed(msgs) if not m["Read"]]


def read(msg_id: str) -> dict:
    m = _api(f"/api/v1/message/{msg_id}")
    atts = [{"name": a["FileName"], "text": _api(f"/api/v1/message/{msg_id}/part/{a['PartID']}")}
            for a in m.get("Attachments") or []]
    return {"id": m["ID"], "from": m["From"]["Address"], "from_name": m["From"]["Name"],
            "to": [t["Address"] for t in m["To"]], "subject": m["Subject"], "text": m["Text"], "attachments": atts}


def mark_read(msg_id: str) -> None:
    _api("/api/v1/messages", "PUT", {"IDs": [msg_id], "Read": True})


def send(to: str, subject: str, body: str, sender: str | None = None,
         attachment: dict | None = None) -> None:
    msg = EmailMessage()
    msg["From"] = sender or f"Meeting Prep <prep@{world()['us']['domain']}>"
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    if attachment:
        msg.add_attachment(attachment["text"].encode(), maintype="text", subtype="plain", filename=attachment["name"])
    host, port = SMTP.split(":")
    with smtplib.SMTP(host, int(port), timeout=10) as s:
        s.send_message(msg)


def as_email(g: dict) -> dict:
    """A golden email in the shape `read()` returns — what a flow receives."""
    name, addr = parseaddr(g["from"])
    return {"id": g["id"], "from": addr, "from_name": name, "to": [world()["us"]["sales"]],
            "subject": g["subject"], "text": g["body"],
            "attachments": [g["attachment"]] if g.get("attachment") else []}


def golden_cases() -> list[dict]:
    """The golden emails as eval cases: {"id", "input": email, "expected": expect}."""
    return [{"id": g["id"], "input": as_email(g), "expected": g["expect"]} for g in golden()]


def send_golden(email_id: str) -> dict:
    """Send a golden email to sales, as the customer would."""
    g = next((e for e in golden() if e["id"] == email_id), None)
    if g is None:
        raise KeyError(f"no golden email {email_id!r}")
    send(world()["us"]["sales"], g["subject"], g["body"], sender=g["from"], attachment=g.get("attachment"))
    return g


def main() -> int:
    args = sys.argv[1:]
    if not args or args[0] == "--list":
        for g in golden():
            print(f"{g['id']:<22} {g['expect']['action']:<6} {parseaddr(g['from'])[1]}")
        return 0
    for a in args:
        g = send_golden(a)
        print(f"sent {a}: {g['subject']!r} from {parseaddr(g['from'])[1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

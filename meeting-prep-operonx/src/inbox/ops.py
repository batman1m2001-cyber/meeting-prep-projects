"""Getting an email out of the inbox."""
from __future__ import annotations

from operonx import op
from prep_world import mail, world

BOT = f"prep@{world()['us']['domain']}"


@op
def fetch(item: dict = None) -> dict:
    """Mailpit's webhook carries the new message's summary; read the whole of it.
    Our own mail (the approval requests) is not a lead and is left alone."""
    email = mail.read(item["ID"])
    mail.mark_read(email["id"])
    return {"email": email, "ours": email["from"].lower() == BOT}


@op
def unread() -> dict:
    """Every unread email — what the morning sweep catches up on."""
    return {"ids": [m["id"] for m in mail.list_new()]}


@op
def each(ids: list = None):
    for i in ids or []:
        yield {"item": {"ID": i}}


@op
def ignore() -> dict:
    return {"outcome": {"action": "ignore"}}

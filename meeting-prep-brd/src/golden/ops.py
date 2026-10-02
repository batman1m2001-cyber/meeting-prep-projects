"""A golden case as the flow receives it: an (opaque) mail id, and no mail."""
from __future__ import annotations

from operonx import op

from tools._golden import email_id


@op
def case(item: dict) -> dict:
    """The eval sends nothing: Human Approval does not email sales."""
    return {"email_id": email_id(item["id"]), "notify": False}

"""What the service doors hand the flows."""
from __future__ import annotations

from operonx import op


@op
def email_request(item: dict) -> dict:
    """POST /prepare {"email_id": "<Mailpit id>"}. Sales is emailed the brief to approve."""
    email_id = (item or {}).get("email_id")
    if not isinstance(email_id, str) or not email_id:
        raise ValueError('POST /prepare needs {"email_id": "<id>"}')
    return {"email_id": email_id, "notify": True}


@op
def approve_request(approval: str, decision: str) -> dict:
    """GET /approve?approval=<id>&decision=approve|reject — the link Human Approval emails to sales."""
    return {"approval_id": int(approval), "decision": decision}

"""Human Approval — "Review and approve the briefing": a person's gate, no
model. The brief is saved as a pending approval and sales is asked, by email,
to approve or reject it; the run ends there, and only the click goes on."""
from __future__ import annotations

import json
from typing import Any, Optional

from operonx import op
from prep_world import world


def _call(call_id: str, name: str, args: dict) -> dict:
    return {"id": call_id, "type": "function",
            "function": {"name": name, "arguments": json.dumps(args, ensure_ascii=False)}}


@op
def approval_call(report: dict) -> dict:
    """The approval request, as a tool call for the harness (which refuses a brief that leaks)."""
    return {"call": _call(f"approval-{report['report_id']}", "approval__request",
                          {"task": "send_brief", "report_id": report["report_id"],
                           "summary": f"Send the brief on {report['title']} to sales and save it to the KB"})}


@op
def review_call(report: dict, approval: dict) -> dict:
    """The email that asks sales to review the brief: the brief, and the two links."""
    body = (f"A brief on {report['title']} is waiting for your review.\n\n"
            f"Approve (send it to sales and save it to the knowledge base):\n{approval['approve_url']}\n\n"
            f"Reject:\n{approval['reject_url']}\n\n---\n\n{report['email_body']}")
    return {"call": _call(f"review-{approval['approval_id']}", "mail__send",
                          {"to": world()["us"]["sales"], "subject": f"[Approve #{approval['approval_id']}] Brief: {report['title']}",
                           "body": body, "approval_id": approval["approval_id"]})}


@op
def waiting(approval: dict, notified: Optional[bool] = None, notify_error: Optional[str] = None) -> dict:
    """Pending, until a person clicks. A review email that could not be sent is an error."""
    if notified is False:
        raise ValueError(f"the review email to sales was not sent: {notify_error}")
    return {"approval": {**approval, "notified": bool(notified)}}


@op
def held(error: Optional[str] = None, data: Any = None) -> dict:
    """Refused before it reached a person (e.g. the brief leaks): nothing waits, nothing is sent."""
    return {"approval": {"approval_id": None, "status": "held", "reason": error, "data": data}}

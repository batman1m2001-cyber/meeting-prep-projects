"""Send Brief / Save to KB: the person's decision, the approved brief, and
what became of it."""
from __future__ import annotations

import json
from typing import Optional

from operonx import op
from prep_world import world

from stores import brd


@op
def decide(approval_id: int, decision: str) -> dict:
    """Record the person's click. A request is decided once: a second click changes nothing."""
    if decision not in ("approve", "reject"):
        raise ValueError(f"decision is approve or reject, not {decision!r}")
    row = brd.decide(approval_id, decision == "approve", by="sales (approval link)")
    if row is None:
        return {"approved": False, "status": "already decided, or no such approval", "report_id": None}
    return {"approved": row["status"] == "approved", "status": row["status"],
            "report_id": row["payload"]["report_id"]}


@op
def approved_brief(report_id: int) -> dict:
    """The brief the person approved, as the Email Agent will send it."""
    r = brd.report(report_id)
    if r is None or not r["email_body"]:
        raise ValueError(f"report {report_id} has no email body")
    return {"report": r, "to": world()["us"]["sales"], "subject": f"Brief: {r['title']}", "body": r["email_body"]}


def _call(call_id: str, name: str, args: dict) -> dict:
    return {"id": call_id, "type": "function",
            "function": {"name": name, "arguments": json.dumps(args, ensure_ascii=False)}}


@op
def save_calls(report: dict, approval_id: int) -> dict:
    """Into the knowledge base, and into the company's memory: two tool calls for the harness."""
    company = report["company_id"] or report["title"]
    return {"tool_calls": [
        _call(f"save-{approval_id}-kb", "kb__save",
              {"company_id": company, "source": f"brief:{report['id']}", "content": report["markdown"]}),
        _call(f"save-{approval_id}-memory", "memory__remember",
              {"subject": company, "kind": "result", "content": report["markdown"], "source": f"approval:{approval_id}"}),
    ]}


@op
def delivered(approval_id: int, message_id: str, status: str, ok: Optional[list] = None,
              error: Optional[list] = None) -> dict:
    """Sent, and both saves done; a failed save is an error, not a quiet half-save."""
    if not ok or not all(ok):
        raise ValueError(f"saving the brief failed: {[e for e in error or [] if e]}")
    return {"outcome": {"approval_id": approval_id, "status": "approved", "sent": [world()["us"]["sales"]],
                        "message_id": message_id, "mail_status": status, "saved": ["kb", "memory"]}}


@op
def not_delivered(approval_id: int, status: str) -> dict:
    return {"outcome": {"approval_id": approval_id, "status": status, "sent": [], "saved": []}}

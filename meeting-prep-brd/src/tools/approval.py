"""approval: important tasks wait here for a person; nothing runs before "approved"."""
from __future__ import annotations

import os

from stores import brd

from tools._server import MCPServer

server = MCPServer("approval")
TASKS = ("send_brief",)


def _link(approval_id: int, decision: str) -> str:
    base = os.environ.get("BRD_PUBLIC_URL", "http://127.0.0.1:8400").rstrip("/")
    return f"{base}/approve?id={approval_id}&decision={decision}"


@server.tool()
def request(task: str, report_id: int, summary: str) -> dict:
    """Ask a person to approve a task (send_brief: send report `report_id` to sales and save it to the KB)."""
    if task not in TASKS:
        raise ValueError(f"task must be one of {TASKS}, got {task!r}")
    r = brd.report(report_id)
    if r is None:
        raise ValueError(f"no report {report_id}")
    approval_id = brd.request_approval(task, {"report_id": report_id, "company_id": r["company_id"],
                                              "summary": summary})
    return {"approval_id": approval_id, "status": "pending",
            "approve_url": _link(approval_id, "approve"), "reject_url": _link(approval_id, "reject")}


@server.tool()
def status(approval_id: int) -> dict:
    """A request's status: pending, approved or rejected, and who decided."""
    a = brd.approval(approval_id)
    if a is None:
        raise ValueError(f"no approval {approval_id}")
    return {"approval_id": approval_id, "task": a["task"], "status": a["status"], "decided_by": a["decided_by"]}


def main() -> None:
    server.run()


if __name__ == "__main__":
    main()

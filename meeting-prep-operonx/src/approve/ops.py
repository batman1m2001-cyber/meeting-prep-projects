"""The second half of approval: a click on the link in the email."""
from __future__ import annotations

from operonx import op
from prep_world import db, mail, world


@op
def decide(draft: str, decision: str) -> dict:
    """Approve → the brief goes to sales and into memory. Reject → nothing.
    A draft is decided once: a second click changes nothing."""
    d = db.decide_draft(int(draft), decision == "approve")
    if d is None:
        return {"reply": {"draft": int(draft), "status": "already decided, or no such draft"}}
    if d["status"] == "approved":
        company = db.find_company(d["company_id"]) or {"name": d["company_id"]}
        mail.send(world()["us"]["sales"], f"Brief: {company['name']}", d["brief"])
        db.remember(d["company_id"], f"brief:{d['id']}", d["brief"])
    return {"reply": {"draft": d["id"], "status": d["status"], "company": d["company_id"]}}

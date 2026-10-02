from operonx import op
from prep_world import db, mail, world


@op
def decide(draft: str, decision: str) -> dict:
    """A draft is decided once: a second click changes nothing (`decided` is then None)."""
    return {"decided": db.decide_draft(int(draft), decision == "approve")}


@op
def send(draft: dict = None) -> dict:
    """Approved → the brief goes to sales."""
    if not draft or draft["status"] != "approved":
        return {"sent": []}
    company = db.find_company(draft["company_id"]) or {"name": draft["company_id"]}
    sales = world()["us"]["sales"]
    mail.send(sales, f"Brief: {company['name']}", draft["brief"])
    return {"sent": [sales]}


@op
def save(draft: dict = None) -> dict:
    """Approved → the brief goes into the knowledge base: memory for the next run."""
    if not draft or draft["status"] != "approved":
        return {"saved": None}
    db.remember(draft["company_id"], f"brief:{draft['id']}", draft["brief"])
    return {"saved": f"brief:{draft['id']}"}


@op
def reply(asked: str, draft: dict = None) -> dict:
    if draft is None:
        return {"reply": {"draft": int(asked), "status": "already decided, or no such draft"}}
    return {"reply": {"draft": draft["id"], "status": draft["status"], "company": draft["company_id"]}}

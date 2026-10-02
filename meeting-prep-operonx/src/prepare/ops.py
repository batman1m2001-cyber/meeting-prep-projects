"""The steps of preparing a brief. One real agent (research); the rest is code
and two plain LLM calls."""
from __future__ import annotations

from email.utils import parseaddr

from operonx import op
from prep_world import db, mail, world
from prep_world.guard import leaks, looks_like_attack, visible_text

from prepare import _mcp

APPROVE_URL = "http://127.0.0.1:8200/approve"


def _domain(address: str) -> str:
    return parseaddr(address)[1].rpartition("@")[2].lower()


def _attachments(email: dict) -> list:
    """Attachments as text, attack lines removed: a real lead's poisoned file
    still gets a brief, and the poison never reaches a model."""
    return [{"name": a["name"], "text": visible_text(a.get("text", ""))} for a in email.get("attachments") or []]


# ── the gate: an attack never reaches a model ─────────────────────────────
@op
def screen(email: dict) -> dict:
    """The sender's own words. An email that is an attack is held whole."""
    hit = looks_like_attack(f"{email.get('subject', '')} {email.get('text', '')}")
    return {"blocked": hit is not None, "reason": hit}


@op
def letter(email: dict) -> dict:
    """The email as the model reads it."""
    parts = [f"From: {email.get('from_name') or ''} <{email['from']}>", f"Subject: {email.get('subject', '')}",
             "", email.get("text", "")]
    for a in _attachments(email):
        parts += ["", f"Attachment {a['name']}:", a["text"]]
    return {"text": "\n".join(parts)}


# ── who is it ──────────────────────────────────────────────────────────────
@op
async def identify(email: dict) -> dict:
    company = await _mcp.call("crm_find_company", domain_or_name=_domain(email["from"]))
    return {"company": company or None, "company_id": (company or {}).get("id"),
            "name": (company or {}).get("name") or _domain(email["from"])}


@op
async def crm(company_id: str = None) -> dict:
    if not company_id:
        return {"contacts": [], "history": []}
    return {"contacts": await _mcp.call("crm_contacts", company_id=company_id),
            "history": await _mcp.call("crm_history", company_id=company_id)}


@op
async def calendar(company_id: str = None) -> dict:
    return {"meetings": await _mcp.call("calendar_meetings", company_id=company_id) if company_id else []}


@op(bound="cpu")
def recall(company: dict = None) -> dict:
    if not company:
        return {"memory": []}
    return {"memory": [r["content"] for r in db.recall(f"{company['name']} {company['industry']}",
                                                         k=3, company_id=company["id"])]}


# ── the research team: three agents, one question each ─────────────────────
@op
def research_tasks(company: dict = None) -> dict:
    name = (company or {}).get("name", "the company")

    def ask(focus: str) -> list:
        return [{"role": "user", "content": f"Research {name} for a sales meeting: {focus}. "
                                            f"Search the web and read what you find. Find out about {name} {focus}."}]

    return {"website": ask("what it does and sells"), "news": ask("news"), "people": ask("team")}


# ── the brief ──────────────────────────────────────────────────────────────
def _answer(final: dict = None) -> str:
    return (final or {}).get("content") or "(no answer)"


# ── the memory agent's merge: every source into one evidence pack ───────────
@op
def evidence(email: dict, company: dict = None, contacts: list = None, history: list = None,
             meetings: list = None, memory: list = None, website: dict = None, news: dict = None,
             people: dict = None) -> dict:
    c = company or {}
    lines = [f"Profile: {c.get('name')} — {c.get('industry')}, {c.get('hq')}, {c.get('size')}. {c.get('about', '')}",
             f"Email from {email.get('from_name') or email['from']}: {email.get('subject', '')} — "
             + " ".join(email.get("text", "").split())]
    lines += [f"Attachment {a['name']}: {a['text']}" for a in _attachments(email) if a["text"]]
    lines += [f"Contact: {p['name']}, {p['title']}" for p in contacts or []]
    lines += [f"History {h['date']} ({h['kind']}): {h['note']}" for h in history or []]
    lines += [f"Meeting {m['starts_at']}: {m['title']}" for m in meetings or []] or ["Meeting: none booked yet"]
    lines += [f"Memory: {m}" for m in memory or []]
    lines += [f"Research ({k}): {_answer(v)}" for k, v in (("website", website), ("news", news), ("people", people))]
    return {"lines": lines}


@op
def dedupe(lines: list = None) -> dict:
    """One evidence pack: a fact that came in twice (from two sources) is said once, in
    first-seen order."""
    return {"text": "\n".join(f"- {ln}" for ln in dict.fromkeys(lines or []))}


@op
def check_brief(brief: str = None, company: dict = None) -> dict:
    us = world()["us"]["domain"]
    problems = leaks(brief or "", (us, (company or {}).get("domain", us)))
    if not company:
        # triage called it a lead, but no company in the CRM matches the sender (e.g. a
        # colleague): hold it for a person rather than ask approval for nobody
        problems = [*problems, "no known company for this sender"]
    return {"ok": not problems, "problems": problems}


@op
def request_approval(email: dict, company: dict, brief: str, deliver: bool = True) -> dict:
    """Save the draft, then ask sales by email. The run ends here; the link continues it.
    `deliver=False` (the eval) does neither: a test run sends nobody anything."""
    sales = world()["us"]["sales"]
    draft_id = None
    if deliver:
        draft_id = db.save_draft(email.get("id", ""), company["id"], email.get("subject", ""), brief)
        mail.send(sales, f"[Approve?] Brief: {company['name']}",
                  f"{brief}\n\nApprove: {APPROVE_URL}?draft={draft_id}&decision=approve\n"
                  f"Reject:  {APPROVE_URL}?draft={draft_id}&decision=reject\n")
    return {"outcome": {"action": "brief", "company": company["id"], "brief": brief, "sent": [sales],
                        "draft_id": draft_id}}


# ── the other ways a run ends ──────────────────────────────────────────────
@op
def blocked(reason: str = None) -> dict:
    return {"outcome": {"action": "block", "company": None, "brief": None, "sent": [], "reason": reason}}


@op
def not_a_lead(intent: str = None) -> dict:
    return {"outcome": {"action": "skip", "company": None, "brief": None, "sent": [], "reason": intent}}


@op
def held(company: dict = None, brief: str = None, problems: list = None) -> dict:
    """The brief failed its check: nothing is sent."""
    return {"outcome": {"action": "held", "company": (company or {}).get("id"), "brief": brief, "sent": [],
                        "reason": problems}}


@op
def screened(blocked: dict = None, skipped: dict = None) -> dict:
    """The email agent's verdict: a lead goes on; a blocked or skipped email ends here."""
    outcome = blocked or skipped
    return {"lead": outcome is None, "outcome": outcome}


@op
def settle(a: dict = None, b: dict = None, c: dict = None, d: dict = None) -> dict:
    """Whichever ending ran."""
    return {"outcome": a or b or c or d}

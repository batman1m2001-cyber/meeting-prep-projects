"""The same system as meeting-prep-operonx, on LangGraph.

    screen ─ attack ─► blocked
      └► triage ─ not a lead ─► not_a_lead
           └► identify ─► crm ∥ calendar ∥ recall ∥ website ∥ news ∥ people ─► evidence
                ─► brief ─► check ─ ok ─► request_approval ─► wait_for_sales (interrupt) ─► finish
                                  └ leak ─► held
"""
from __future__ import annotations

import operator
import os
from email.utils import parseaddr
from typing import Annotated, Any, Optional, TypedDict

from langchain.agents import create_agent
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from prep_world import MODEL_KEY, MODEL_URL, db, mail, world
from prep_world.guard import leaks, looks_like_attack, visible_text

from prep.prompts import BRIEF, RESEARCH, TRIAGE
from prep.tools import RESEARCH_TOOLS, mcp

APPROVE_URL = "http://127.0.0.1:8300/approve"
MODEL = ChatOpenAI(model=os.environ.get("PREP_MODEL", "gpt-4o-mini"), base_url=MODEL_URL, api_key=MODEL_KEY)


class State(TypedDict, total=False):
    email: dict
    deliver: bool
    thread: str
    reason: Optional[str]
    is_lead: bool
    intent: Optional[str]
    company: Optional[dict]
    contacts: list
    history: list
    meetings: list
    memory: list
    research: Annotated[dict, operator.or_]  # three agents write here in parallel
    evidence: str
    brief: str
    problems: list
    outcome: dict
    decision: str


def _attachments(email: dict) -> list:
    return [{"name": a["name"], "text": visible_text(a.get("text", ""))} for a in email.get("attachments") or []]


# ── nodes ──────────────────────────────────────────────────────────────────
def screen(s: State) -> dict:
    e = s["email"]
    return {"reason": looks_like_attack(f"{e.get('subject', '')} {e.get('text', '')}")}


def blocked(s: State) -> dict:
    return {"outcome": {"action": "block", "company": None, "brief": None, "sent": [], "reason": s["reason"]}}


triage_chain = ChatPromptTemplate.from_messages([("system", TRIAGE), ("user", "{letter}")]) | MODEL | JsonOutputParser()


async def triage(s: State) -> dict:
    e = s["email"]
    parts = [f"From: {e.get('from_name') or ''} <{e['from']}>", f"Subject: {e.get('subject', '')}", "", e.get("text", "")]
    for a in _attachments(e):
        parts += ["", f"Attachment {a['name']}:", a["text"]]
    out = await triage_chain.ainvoke({"letter": "\n".join(parts)})
    return {"is_lead": bool(out["is_lead"]), "intent": out.get("intent")}


def not_a_lead(s: State) -> dict:
    return {"outcome": {"action": "skip", "company": None, "brief": None, "sent": [], "reason": s.get("intent")}}


async def identify(s: State) -> dict:
    domain = parseaddr(s["email"]["from"])[1].rpartition("@")[2].lower()
    return {"company": await mcp("crm_find_company", domain_or_name=domain) or None}


async def crm(s: State) -> dict:
    cid = (s.get("company") or {}).get("id")
    if not cid:
        return {"contacts": [], "history": []}
    return {"contacts": await mcp("crm_contacts", company_id=cid), "history": await mcp("crm_history", company_id=cid)}


async def calendar(s: State) -> dict:
    cid = (s.get("company") or {}).get("id")
    return {"meetings": await mcp("calendar_meetings", company_id=cid) if cid else []}


def recall(s: State) -> dict:
    c = s.get("company")
    if not c:
        return {"memory": []}
    return {"memory": [r["content"] for r in db.recall(f"{c['name']} {c['industry']}", k=3, company_id=c["id"])]}


researcher = create_agent(MODEL, tools=RESEARCH_TOOLS, system_prompt=RESEARCH)


def research(focus_key: str, focus: str):
    async def node(s: State) -> dict:
        name = (s.get("company") or {}).get("name", "the company")
        ask = (f"Research {name} for a sales meeting: {focus}. "
               f"Search the web and read what you find. Find out about {name} {focus}.")
        out = await researcher.ainvoke({"messages": [{"role": "user", "content": ask}]}, {"recursion_limit": 10})
        return {"research": {focus_key: out["messages"][-1].content}}
    return node


def evidence(s: State) -> dict:
    c, e = s.get("company") or {}, s["email"]
    lines = [f"Profile: {c.get('name')} — {c.get('industry')}, {c.get('hq')}, {c.get('size')}. {c.get('about', '')}",
             f"Email from {e.get('from_name') or e['from']}: {e.get('subject', '')} — " + " ".join(e.get("text", "").split())]
    lines += [f"Attachment {a['name']}: {a['text']}" for a in _attachments(e) if a["text"]]
    lines += [f"Contact: {p['name']}, {p['title']}" for p in s.get("contacts") or []]
    lines += [f"History {h['date']} ({h['kind']}): {h['note']}" for h in s.get("history") or []]
    lines += [f"Meeting {m['starts_at']}: {m['title']}" for m in s.get("meetings") or []] or ["Meeting: none booked yet"]
    lines += [f"Memory: {m}" for m in s.get("memory") or []]
    lines += [f"Research ({k}): {s['research'].get(k, '(no answer)')}" for k in ("website", "news", "people")]
    return {"evidence": "\n".join(f"- {ln}" for ln in lines)}


brief_chain = ChatPromptTemplate.from_messages([("system", BRIEF), ("user", "Company: {company}\n\nEvidence:\n{evidence}")]) | MODEL


async def brief(s: State) -> dict:
    name = (s.get("company") or {}).get("name") or parseaddr(s["email"]["from"])[1].rpartition("@")[2]
    return {"brief": (await brief_chain.ainvoke({"company": name, "evidence": s["evidence"]})).content}


def check(s: State) -> dict:
    us = world()["us"]["domain"]
    return {"problems": leaks(s["brief"], (us, (s.get("company") or {}).get("domain", us)))}


def held(s: State) -> dict:
    return {"outcome": {"action": "held", "company": (s.get("company") or {}).get("id"), "brief": s["brief"],
                        "sent": [], "reason": s["problems"]}}


def request_approval(s: State) -> dict:
    """Save the draft and ask sales. Its own node: on resume LangGraph re-runs the
    node that called interrupt() from the top, so side effects must not live there."""
    c, sales = s["company"], world()["us"]["sales"]
    outcome = {"action": "brief", "company": c["id"], "brief": s["brief"], "sent": [sales]}
    if not s.get("deliver", True):
        return {"outcome": outcome}
    draft_id = db.save_draft(s["email"].get("id", ""), c["id"], s["email"].get("subject", ""), s["brief"])
    link = f"{APPROVE_URL}?thread={s['thread']}&draft={draft_id}"
    mail.send(sales, f"[Approve?] Brief: {c['name']}",
              f"{s['brief']}\n\nApprove: {link}&decision=approve\nReject:  {link}&decision=reject\n")
    return {"outcome": {**outcome, "draft_id": draft_id}}


def wait_for_sales(s: State) -> dict:
    """The run pauses here until the link is clicked."""
    return {"decision": interrupt({"draft_id": s["outcome"]["draft_id"]})}


def finish(s: State) -> dict:
    d = db.decide_draft(s["outcome"]["draft_id"], s["decision"] == "approve")
    if d and d["status"] == "approved":
        mail.send(world()["us"]["sales"], f"Brief: {s['company']['name']}", d["brief"])
        db.remember(d["company_id"], f"brief:{d['id']}", d["brief"])
    return {"outcome": {**s["outcome"], "decision": s["decision"]}}


# ── wiring ─────────────────────────────────────────────────────────────────
def build(checkpointer: Any = None):
    g = StateGraph(State)
    for name, fn in [("screen", screen), ("blocked", blocked), ("triage", triage), ("not_a_lead", not_a_lead),
                     ("identify", identify), ("crm", crm), ("calendar", calendar), ("recall", recall),
                     ("website", research("website", "what it does and sells")), ("news", research("news", "news")),
                     ("people", research("people", "team")), ("evidence", evidence), ("brief", brief),
                     ("check", check), ("held", held), ("request_approval", request_approval),
                     ("wait_for_sales", wait_for_sales), ("finish", finish)]:
        g.add_node(name, fn)
    fan = ["crm", "calendar", "recall", "website", "news", "people"]
    g.add_edge(START, "screen")
    g.add_conditional_edges("screen", lambda s: "blocked" if s.get("reason") else "triage", ["blocked", "triage"])
    g.add_conditional_edges("triage", lambda s: "identify" if s["is_lead"] else "not_a_lead", ["identify", "not_a_lead"])
    for n in fan:
        g.add_edge("identify", n)
    g.add_edge(fan, "evidence")
    g.add_edge("evidence", "brief")
    g.add_edge("brief", "check")
    g.add_conditional_edges("check", lambda s: "held" if s["problems"] else "request_approval", ["held", "request_approval"])
    g.add_conditional_edges("request_approval", lambda s: "wait_for_sales" if s["outcome"].get("draft_id") else END,
                            ["wait_for_sales", END])
    g.add_edge("wait_for_sales", "finish")
    for n in ("blocked", "not_a_lead", "held", "finish"):
        g.add_edge(n, END)
    return g.compile(checkpointer=checkpointer or InMemorySaver())


GRAPH = build()

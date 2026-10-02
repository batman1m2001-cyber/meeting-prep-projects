"""The Email Agent's own steps: its two tasks, and its two answers checked."""
from __future__ import annotations

import json
from typing import Optional

from operonx import op

from .._shared import _messages
from .._shared._prompts import PROMPTS

FACTS = ("sender", "sender_email", "company_hint", "domain", "content_summary", "intent",
         "is_customer_or_partner", "is_new_customer", "attachments")


@op
def opening(email_id: str) -> dict:
    """Task "analyse": a new email arrived."""
    task = {"task": "analyse", "email_id": email_id}
    return {"messages": [{"role": "system", "content": PROMPTS["email_agent"]},
                         {"role": "user", "content": json.dumps(task)}]}


@op
def email_facts(email_id: str, content: Optional[str] = None, messages: Optional[list] = None,
                alerts: Optional[list] = None) -> dict:
    """The agent's answer, checked, and what happens next.

    `block` is decided by the screen, not the model: an email whose own words
    matched an attack pattern. Otherwise the model's `is_customer_or_partner`
    decides `brief` or `skip`. An answer about an email it never read is an error.
    """
    attack = next((a for a in alerts or [] if a["tool"] == "mail__read" and a["kind"] == "attack"), None)
    if attack:
        return {"facts": None, "action": "block", "reason": f"attack pattern in the email: {attack['match']!r}",
                "screened": alerts}
    read = [e for e in _messages.results(messages, "mail__read") if e.get("id") == email_id]
    if not read:
        raise ValueError(f"the Email Agent answered without reading {email_id}")
    facts = _messages.answer(content, FACTS)
    lead = facts["is_customer_or_partner"] is True
    return {"facts": facts, "action": "brief" if lead else "skip",
            "reason": facts["intent"] if lead else f"not a customer or partner email: {facts['intent']}",
            "screened": alerts or []}


@op
def send_opening(approval_id: int, to: str, subject: str, body: str) -> dict:
    """Task "send": an approved email to send."""
    task = {"task": "send", "approval_id": approval_id, "to": to, "subject": subject, "body": body}
    return {"messages": [{"role": "system", "content": PROMPTS["email_agent"]},
                         {"role": "user", "content": json.dumps(task, ensure_ascii=False)}]}


@op
def sent(content: Optional[str] = None, messages: Optional[list] = None, alerts: Optional[list] = None) -> dict:
    """The send, checked against what mail__send actually returned."""
    done = _messages.results(messages, "mail__send")
    if not done:
        why = _messages.refusals(messages, "mail__send") or ["mail__send was never called"]
        raise ValueError(f"the brief was not sent: {why[-1]}")
    answer = _messages.answer(content, ("message_id", "status"))
    if answer["message_id"] != done[-1]["message_id"]:
        raise ValueError(f"the Email Agent reported {answer['message_id']!r}, mail__send sent {done[-1]['message_id']!r}")
    return {"message_id": answer["message_id"], "status": answer["status"], "screened": alerts or []}

"""The Report Generation Agent's task and its answer, checked against what
its tools actually rendered."""
from __future__ import annotations

import json
from typing import Optional

from operonx import op

from .._shared import _messages
from .._shared._prompts import PROMPTS


@op
def opening(company: dict, facts: dict, context: list, profile: dict) -> dict:
    task = {"company": company, "email": facts, "context": context, "user_profile": profile}
    return {"messages": [{"role": "system", "content": PROMPTS["report_agent"]},
                         {"role": "user", "content": json.dumps(task, ensure_ascii=False)}]}


@op
def report(company: dict, content: Optional[str] = None, messages: Optional[list] = None,
           alerts: Optional[list] = None) -> dict:
    """The report the tools stored, in both formats — never the model's say-so."""
    report_id = _messages.answer(content, ("report_id",))["report_id"]
    rendered = [r for r in _messages.results(messages, "report__render_markdown") if r["report_id"] == report_id]
    emailed = [r for r in _messages.results(messages, "report__email_body") if r["report_id"] == report_id]
    if not rendered or not emailed:
        raise ValueError(f"report {report_id} was not both rendered and turned into an email")
    return {"report": {"report_id": report_id, "company_id": company["company_id"],
                       "title": company["company_name"], "markdown": rendered[-1]["markdown"],
                       "subject": emailed[-1]["subject"], "email_body": emailed[-1]["body"]},
            "screened": alerts or []}

"""The Memory Agent's task and its answer, checked."""
from __future__ import annotations

import json
from typing import Optional

from operonx import op

from .._shared import _messages
from .._shared._prompts import PROMPTS


@op
def opening(company: dict, facts: dict, research: dict, meetings: list, info: dict) -> dict:
    findings = {"company": company, "email": facts, "web_research": research, "calendar": meetings,
                "company_info": info}
    return {"messages": [{"role": "system", "content": PROMPTS["memory_agent"]},
                         {"role": "user", "content": json.dumps(findings, ensure_ascii=False)}]}


@op
def context(content: Optional[str] = None, alerts: Optional[list] = None) -> dict:
    answer = _messages.answer(content, ("context", "new_since_last", "user_profile"))
    if not answer["context"]:
        raise ValueError("the Memory Agent merged nothing")
    return {"context": answer["context"], "new_since_last": answer["new_since_last"],
            "profile": answer["user_profile"], "screened": alerts or []}

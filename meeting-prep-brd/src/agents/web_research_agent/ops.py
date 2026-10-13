"""The Web Research Agent's task and its answer, checked."""
from __future__ import annotations

import json
from typing import Optional

from operonx import op

from .._shared import _messages

RESEARCH = ("website", "field", "products", "size", "headquarters", "news", "people", "sources")


@op
def opening(company: dict) -> dict:
    task = {"task": "research this company", "company": company}
    return {"input": json.dumps(task, ensure_ascii=False)}


@op
def research(content: Optional[str] = None, alerts: Optional[list] = None) -> dict:
    return {"research": _messages.answer(content, RESEARCH), "screened": alerts or []}

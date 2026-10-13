"""The Company Info Agent's task and its answer, checked."""
from __future__ import annotations

import json
from typing import Optional

from operonx import op

from .._shared import _messages


@op
def opening(company: dict) -> dict:
    task = {"task": "get what we hold about this company", "company": company}
    return {"input": json.dumps(task, ensure_ascii=False)}


@op
def company_info(content: Optional[str] = None, alerts: Optional[list] = None) -> dict:
    return {"info": _messages.answer(content, ("profile", "contacts", "history", "kb_notes")), "screened": alerts or []}

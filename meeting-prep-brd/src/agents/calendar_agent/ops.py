"""The Calendar Agent's task and its answer, checked."""
from __future__ import annotations

import json
from typing import Optional

from operonx import op

from .._shared import _messages


@op
def opening(company: dict) -> dict:
    """The task, as the agent's first message (its prompt is its instructions)."""
    task = {"task": "find upcoming meetings with this company", "company": company}
    return {"input": json.dumps(task, ensure_ascii=False)}


@op
def meetings(content: Optional[str] = None, alerts: Optional[list] = None) -> dict:
    found = _messages.answer(content, ("meetings",))["meetings"]
    if not isinstance(found, list):
        raise ValueError(f"the Calendar Agent's meetings are not a list: {found!r}")
    return {"meetings": found, "screened": alerts or []}

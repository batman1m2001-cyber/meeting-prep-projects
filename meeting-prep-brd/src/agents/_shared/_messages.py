"""Reading an agent's conversation: its final JSON answer, and the results
its tools returned (each tool message is a JSON envelope, see `ops.as_data`)."""
from __future__ import annotations

import json
import re
from typing import Any

_FENCE = re.compile(r"^\s*```[a-zA-Z]*\s*\n(.*?)\n?```\s*$", re.S)


def answer(content: str, required: tuple[str, ...]) -> dict:
    """The agent's final answer as a JSON object holding `required`; raises when it is not one."""
    text = (content or "").strip()
    fenced = _FENCE.match(text)
    try:
        value = json.loads(fenced.group(1) if fenced else text)
    except ValueError as e:
        raise ValueError(f"the agent's answer is not JSON: {text[:200]!r}") from e
    if not isinstance(value, dict):
        raise ValueError(f"the agent's answer is not a JSON object: {text[:200]!r}")
    missing = [k for k in required if k not in value]
    if missing:
        raise ValueError(f"the agent's answer lacks {missing}: {text[:200]!r}")
    return value


def envelope(content: str) -> dict:
    return json.loads(content)


def results(messages: list[dict] | None, tool: str) -> list[Any]:
    """What every successful call of `tool` returned, in order."""
    out = []
    for m in messages or []:
        if isinstance(m, dict) and m.get("role") == "tool" and m.get("name") == tool:
            e = envelope(m["content"])
            if e["ok"]:
                out.append(e["data"])
    return out


def refusals(messages: list[dict] | None, tool: str) -> list[str]:
    """Why each failed call of `tool` failed, in order."""
    return [envelope(m["content"])["error"] for m in messages or []
            if isinstance(m, dict) and m.get("role") == "tool" and m.get("name") == tool
            and not envelope(m["content"])["ok"]]

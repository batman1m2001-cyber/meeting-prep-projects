"""The steps every agent shares: the loop's (model turn, reply check, tool
results) and the tool harness's six, one op per step.

Tool harness, per call (`graph.tool_call`):
    validate      the arguments against the tool's schema
    authenticate  the caller's identity
    authorize     its scopes: this identity, this tool, these arguments
    rate_limit    per identity and tool
    audit         every call, allowed or refused, into brd.audit
    execute       over MCP, with a timeout; a failure comes back as a value
then `as_data` turns the result into the tool message the model reads:
screened for injection, and quoted as data.

A refused step hands its `error` on; the steps after it record it and pass
it along, so a refused call is still audited and still answered.
"""
from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any, Optional

import jsonschema
from operonx import op
from prep_world.guard import looks_like_attack, visible_text

from stores import brd

from . import _mcp, _scopes

TRUNCATED = ("length", "max_tokens", "content_filter")


# ── the loop ───────────────────────────────────────────────────────────────
@op
async def tool_schemas(agent: str) -> dict:
    """The tools this agent may call, as the model is shown them — and no others."""
    catalog = await _mcp.catalog()
    missing = [t for t in _scopes.tools_of(agent) if t not in catalog]
    if missing:
        raise ValueError(f"{agent}: no MCP server provides {missing}")
    return {"tools": [{"type": "function",
                       "function": {"name": t, "description": catalog[t]["description"],
                                    "parameters": catalog[t]["schema"]}}
                      for t in _scopes.tools_of(agent)]}


@op
def count_turn(turns: int = 0, max_turns: int = 8) -> dict:
    """One more turn. On the last one the model may not call a tool: it must answer."""
    turns = (turns or 0) + 1
    return {"turns": turns, "tool_choice": "none" if turns >= max_turns else "auto"}


@op
def reply(content: Optional[str] = None, tool_calls: Optional[list] = None,
          finish_reason: Optional[str] = None) -> dict:
    """The model's turn, checked: a cut or empty reply is an error, never an answer."""
    if finish_reason in TRUNCATED:
        raise ValueError(f"the model's reply was cut off ({finish_reason})")
    calls = [c for c in tool_calls or [] if isinstance(c, dict)]
    if not calls and not (content or "").strip():
        raise ValueError("the model replied with neither text nor a tool call")
    message: dict[str, Any] = {"id": f"assistant-{uuid.uuid4().hex[:12]}", "role": "assistant",
                               "content": content or ""}
    if calls:
        message["tool_calls"] = calls
    return {"messages": [message], "tool_calls": calls, "done": not calls, "content": content or ""}


@op
def each_call(tool_calls: Optional[list] = None):
    """One frame per tool call the model asked for."""
    for call in tool_calls or []:
        yield {"call": call}


@op
def tool_results(messages: Any = None, alerts: Any = None) -> dict:
    """A turn's tool messages and screen alerts, as lists for the loop's cells."""
    def as_list(v: Any) -> list:
        return [v] if isinstance(v, dict) else [x for x in v or [] if isinstance(x, dict)]
    return {"messages": as_list(messages), "alerts": as_list(alerts)}


@op
def parsed(error: Optional[str] = None) -> dict:
    """Raise when the model call before it could not parse its reply."""
    if error:
        raise ValueError(f"the model's reply did not parse: {str(error).strip().splitlines()[0]}")
    return {"ok": True}


# ── the tool harness ───────────────────────────────────────────────────────
@op
async def validate(call: dict) -> dict:
    """Step 1: a known tool, arguments that are a JSON object matching its schema."""
    fn = call.get("function") or call
    tool, raw = fn.get("name") or "", fn.get("arguments")
    base = {"call_id": call.get("id") or "", "tool": tool, "args": {}}
    catalog = await _mcp.catalog()
    if tool not in catalog:
        return {**base, "error": f"no tool named {tool!r}"}
    try:
        args = json.loads(raw) if isinstance(raw, str) else dict(raw or {})
        jsonschema.validate(args, catalog[tool]["schema"])
    except (ValueError, TypeError, jsonschema.ValidationError) as e:
        return {**base, "error": f"bad arguments for {tool}: {getattr(e, 'message', e)}"}
    return {**base, "args": args, "error": None}


@op
def authenticate(agent: str, error: Optional[str] = None) -> dict:
    """Step 2: the caller is a known identity."""
    if error is None and agent not in _scopes.IDENTITIES:
        error = f"unknown identity {agent!r}"
    return {"identity": agent, "error": error}


@op(bound="cpu")
def authorize(identity: str, tool: str, args: dict, error: Optional[str] = None) -> dict:
    """Step 3: this identity may make this call (its tools; mail only to sales,
    only with an approved approval; nothing outbound that leaks)."""
    return {"error": error or _scopes.refusal(identity, tool, args)}


@op
def rate_limit(identity: str, tool: str, error: Optional[str] = None) -> dict:
    """Step 4: per identity and tool, per minute. A refused call is not counted."""
    return {"error": error or _scopes.over_limit(identity, tool)}


@op(bound="cpu")
def audit(identity: str, tool: str, args: dict, error: Optional[str] = None) -> dict:
    """Step 5: every call into the audit log, allowed or refused."""
    return {"audit_id": brd.log_call(identity, tool or "?", args, error or "allowed")}


@op
async def execute(tool: str, args: dict, error: Optional[str] = None) -> dict:
    """Step 6: the call over MCP, with a timeout. Never raises: a failure is a value."""
    if error:
        return {"ok": False, "result": None, "error": error}
    try:
        result = await asyncio.wait_for(_mcp.call(tool, args), timeout=_scopes.TIMEOUT_S)
    except asyncio.TimeoutError:
        return {"ok": False, "result": None, "error": f"{tool} timed out after {_scopes.TIMEOUT_S:g}s"}
    except Exception as e:  # noqa: BLE001 — any failure is reported to the model, not raised
        return {"ok": False, "result": None, "error": f"{tool} failed: {e}"}
    return {"ok": True, "result": result, "error": None}


@op
def as_data(call_id: str, tool: str, ok: bool, result: Any = None, error: Optional[str] = None) -> dict:
    """The tool message: the result screened for injection, then quoted as data.

    An inbound email whose own words are an attack is withheld whole (alert
    `attack`); instruction-shaped lines anywhere else are dropped (alert
    `cleaned`). The model reads a JSON envelope `{tool, ok, data, error}`;
    a step that is not an agent reads `ok`, `data` and `error` directly.
    """
    data, alert = _screen(tool, result) if ok else (None, None)
    content = json.dumps({"tool": tool, "ok": ok, "data": data, "error": error}, ensure_ascii=False, default=str)
    return {"message": {"role": "tool", "tool_call_id": call_id, "name": tool, "content": content},
            "alert": alert, "ok": ok, "data": data, "error": error}


def _screen(tool: str, result: Any) -> tuple[Any, Optional[dict]]:
    if tool == "mail__read" and isinstance(result, dict):
        hit = looks_like_attack(f"{result.get('subject', '')}\n{result.get('text', '')}")
        if hit:
            withheld = {"id": result.get("id"), "from": result.get("from"),
                        "withheld": "this email matched an attack pattern and is not shown"}
            return withheld, {"tool": tool, "kind": "attack", "match": hit}
    dropped: list[str] = []
    clean = _clean(result, dropped)
    return clean, ({"tool": tool, "kind": "cleaned", "match": dropped[0]} if dropped else None)


def _clean(value: Any, dropped: list[str]) -> Any:
    """Drop instruction-shaped lines from every string in a result."""
    if isinstance(value, str):
        hit = looks_like_attack(value)
        if hit:
            dropped.append(hit)
            return visible_text(value)
        return value
    if isinstance(value, list):
        return [_clean(v, dropped) for v in value]
    if isinstance(value, dict):
        return {k: _clean(v, dropped) for k, v in value.items()}
    return value

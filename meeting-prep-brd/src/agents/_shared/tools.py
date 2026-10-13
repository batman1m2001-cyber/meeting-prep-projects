"""An agent's tools: each one its MCP tool, run through the six-step harness.

`harness_tools("calendar_agent")` is the Calendar Agent's tools as AgentOp
runs them. Each is named and described as its MCP server describes it, with
that tool's schema (what the model is shown), and a call runs the harness
graph (`graph.tool_call`: validate → authenticate → authorize → rate_limit →
audit → execute → as_data) as a step of the agent's run. So the trace reads
`agent → turn → <tool> → tool_call → validate …`, and the model reads the
harness's envelope `{tool, ok, data, error}` as before.

The tool hands the model's arguments to the harness untouched: step 1
validates them against the schema, so a bad call is refused *and audited*,
as the brief asks.

The schemas are read from the in-repo servers (`src/tools/*.py`) when this
module loads: an agent's tools must exist when its graph is defined, and the
running servers can only be asked once connected. `tests/unit/test_harness.py`
checks they are what the running servers list.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from operonx import invoke
from operonx.agents import Agent, Model, RunContext, UsageLimits
from operonx.agents.tools.tool import Tool, ToolSpec
from pydantic import BaseModel

from . import _mcp, _scopes, _screens
from ._prompts import PROMPTS
from .graph import tool_call


@lru_cache(maxsize=1)
def catalog() -> dict[str, dict]:
    """Every tool of every in-repo MCP server, by its model-facing name
    (`calendar__meetings`): its description and argument schema."""
    out: dict[str, dict] = {}
    for name in _mcp.SERVERS:
        server = importlib.import_module(f"tools.{name}").server
        # the server's own registry, read without starting it (what its
        # list_tools answers once it runs)
        for t in server._tool_manager.list_tools():
            out[f"{name}{_mcp.SEP}{t.name}"] = {"description": t.description or "", "schema": t.parameters}
    return out


class _Raw(BaseModel):
    """No fields: the harness validates the arguments, not dispatch."""


@dataclass(frozen=True)
class HarnessTool(Tool):
    """A tool whose arguments go to the harness as the model wrote them."""

    def validate(self, args: dict[str, Any]) -> dict[str, Any]:
        return {"args": dict(args)}


def _harnessed(identity: str, name: str, description: str, schema: dict) -> HarnessTool:
    async def call(ctx: RunContext, args: dict) -> str:
        out = await invoke(tool_call, agent=identity,
                           call={"id": ctx.tool_call_id or "", "function": {"name": name, "arguments": args}})
        _screens.note(ctx.run_id, out.get("alert"))
        return out["message"]["content"]

    call.__name__ = name
    spec = ToolSpec(name=name, description=description, params_schema=schema,
                    sequential=False,       # a turn's calls run at once, as `run_tools` ran them
                    max_result_chars=200_000)  # the envelope is the data: never cut it
    return HarnessTool(spec=spec, function=call, takes_context=True, args_model=_Raw,
                       kind="graph", target=tool_call)


def harness_tools(identity: str) -> list[HarnessTool]:
    """The tools `identity` may call (`scopes.yaml`), and no others."""
    known = catalog()
    missing = [t for t in _scopes.tools_of(identity) if t not in known]
    if missing:
        raise ValueError(f"{identity}: no MCP server provides {missing}")
    return [_harnessed(identity, t, known[t]["description"], known[t]["schema"]) for t in _scopes.tools_of(identity)]


def agent(identity: str, turns: int) -> Agent:
    """One of the brief's agents: its prompt, the `agent` model, its harnessed
    tools, and its turns — on the last one it may not call a tool, it answers."""
    return Agent(name=identity, model=Model("agent"), instructions=PROMPTS[identity],
                 tools=harness_tools(identity), limits=UsageLimits(turns=turns))

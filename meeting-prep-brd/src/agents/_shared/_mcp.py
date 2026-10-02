"""The MCP servers (`tools/`), started once per event loop and shared by every
tool call: their catalog (what the model is shown) and the call itself."""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Any

from operonx.agents.mcp import MCPClient, MCPServer

SERVERS = ("mail", "crm", "calendar", "kb", "memory", "report", "approval", "web")
SRC = Path(__file__).resolve().parents[2]
SEP = "__"                                      # mail__read: server, tool


class _Pool:
    loop: asyncio.AbstractEventLoop | None = None
    lock: asyncio.Lock | None = None
    clients: dict[str, MCPClient] = {}
    catalog: dict[str, dict] = {}


def _server(name: str) -> MCPServer:
    env = {k: v for k, v in os.environ.items() if k.startswith(("PREP_", "OPENAI_", "BRD_")) or k == "PATH"}
    env["PYTHONPATH"] = str(SRC)
    return MCPServer(name=name, command=sys.executable, args=["-m", f"tools.{name}"], env=env,
                     cwd=str(SRC.parent))


async def _connected() -> dict[str, MCPClient]:
    loop = asyncio.get_running_loop()
    if _Pool.loop is not loop:                      # a new loop (a test, a restart): new connections
        _Pool.loop, _Pool.lock, _Pool.clients, _Pool.catalog = loop, asyncio.Lock(), {}, {}
    async with _Pool.lock:
        if not _Pool.clients:
            clients = await asyncio.gather(*(MCPClient(_server(n)).connect() for n in SERVERS))
            _Pool.clients = dict(zip(SERVERS, clients))
            _Pool.catalog = {
                f"{n}{SEP}{t.name}": {"server": n, "tool": t.name, "description": t.description or "",
                                      "schema": t.input_schema if hasattr(t, "input_schema") else t.inputSchema}
                for n, c in _Pool.clients.items() for t in c.tools
            }
    return _Pool.clients


async def catalog() -> dict[str, dict]:
    """Every tool of every server, by its model-facing name (`mail__read`)."""
    await _connected()
    return _Pool.catalog


async def call(name: str, args: dict[str, Any]) -> Any:
    """One tool's value (not its text). Raises on a refused or failed call."""
    clients = await _connected()
    server, tool = name.split(SEP, 1)
    return await clients[server].call_value(tool, args)

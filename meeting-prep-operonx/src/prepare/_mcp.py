"""One connection to the CRM/calendar MCP server, opened on first use."""
from __future__ import annotations

import asyncio
import os
import sys
from typing import Any

from operonx.agents.mcp import MCPClient, MCPServer

_client: MCPClient | None = None
_lock: asyncio.Lock | None = None


async def call(tool: str, **args: Any) -> Any:
    """Call a tool of the `crm` server; its value, not its text."""
    global _client, _lock
    _lock = _lock or asyncio.Lock()
    async with _lock:
        if _client is None:
            # a stdio child gets a bare environment: hand it the world's settings (PREP_DB_URL, …)
            env = {k: v for k, v in os.environ.items() if k.startswith("PREP_")}
            server = MCPServer(name="crm", command=sys.executable, args=["-m", "prep_world.mcp_server"], env=env)
            _client = await MCPClient(server).connect()
    return await _client.call_value(tool, args)

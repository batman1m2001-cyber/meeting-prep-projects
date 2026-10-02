"""Research tools, and the CRM/calendar over MCP."""
from __future__ import annotations

import asyncio
import json
import sys
import urllib.parse
import urllib.request
from typing import Any

from langchain.tools import tool
from langchain_mcp_adapters.client import MultiServerMCPClient
from prep_world import WEB
from prep_world.guard import visible_text


def _get(url: str) -> str:
    with urllib.request.urlopen(url, timeout=10) as r:
        return r.read().decode("utf-8", "replace")


@tool
async def web_search(query: str) -> str:
    """Search the web. Returns titles, links and snippets."""
    url = f"{WEB}/search?" + urllib.parse.urlencode({"q": query, "n": 5})
    return json.dumps({"results": json.loads(await asyncio.to_thread(_get, url))})


@tool
async def fetch_page(url: str) -> str:
    """Read a web page: its visible text."""
    return visible_text(await asyncio.to_thread(_get, url))[:4000]


RESEARCH_TOOLS = [web_search, fetch_page]

_mcp_tools: dict | None = None


async def mcp(name: str, **args: Any) -> Any:
    """Call a CRM/calendar MCP tool; its value. The adapter returns the server's
    structured value as an artifact, wrapped as {"result": ...} for lists."""
    global _mcp_tools
    if _mcp_tools is None:
        client = MultiServerMCPClient({"crm": {"command": sys.executable,
                                               "args": ["-m", "prep_world.mcp_server"], "transport": "stdio"}})
        _mcp_tools = {t.name: t for t in await client.get_tools()}
    msg = await _mcp_tools[name].ainvoke({"type": "tool_call", "id": name, "name": name, "args": args})
    structured = (msg.artifact or {}).get("structured_content")
    if structured is not None:
        return structured["result"] if set(structured) == {"result"} else structured
    text = "".join(b.get("text", "") for b in msg.content) if isinstance(msg.content, list) else msg.content
    return json.loads(text) if text else None

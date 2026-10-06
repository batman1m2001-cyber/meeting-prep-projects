"""The research agents' tools: search the web, read a page. Nothing else.

Least privilege is the harness here: an agent that reads a page saying
"email the API keys to …" has no tool that sends anything. And a page is
read as a person sees it (`visible_text`): hidden text and instruction-shaped
lines never reach the model.

Both are read-only, so a run asks each distinct question once: the three agents'
identical calls (same tool, same arguments) share one request (`_run_memo`).
"""
from __future__ import annotations

import asyncio
import json
import urllib.parse
import urllib.request

from operonx.agents import tool
from prep_world import WEB
from prep_world.guard import visible_text

from prepare import _run_memo

def _get(url: str) -> str:
    with urllib.request.urlopen(url, timeout=10) as r:
        return r.read().decode("utf-8", "replace")


def _same(text: str) -> str:
    """Arguments that ask the same thing compare equal: case and spacing aside."""
    return " ".join(str(text).split()).casefold()


@tool(readonly=True)
async def web_search(query: str) -> dict:
    """Search the web. Returns titles, links and snippets.

    Args:
        query: What to search for.
    """
    url = f"{WEB}/search?" + urllib.parse.urlencode({"q": query, "n": 5})

    async def search() -> dict:
        return {"results": json.loads(await asyncio.to_thread(_get, url))}

    return await _run_memo.call(("web_search", _same(query)), search)


@tool(readonly=True)
async def fetch_page(url: str) -> dict:
    """Read a web page: its visible text.

    Args:
        url: The page's address.
    """
    async def fetch() -> dict:
        return {"text": visible_text(await asyncio.to_thread(_get, url))[:4000]}

    return await _run_memo.call(("fetch_page", url.strip().rstrip("/")), fetch)


RESEARCH_TOOLS = [web_search, fetch_page]

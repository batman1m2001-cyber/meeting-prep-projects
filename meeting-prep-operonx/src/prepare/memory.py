"""What the research agents already know: company memory, OperonX's agent memory.

Two kinds of memory in this flow, on purpose:

    ops.recall        code picks — the workflow fetches the company's notes once and
                      hands them to the brief.
    CompanyMemory     the agent's own — an OperonX `MemoryProvider`, consulted by every
                      research agent each turn (context zone → `recalled`), so it starts
                      from what past meetings and approved briefs already say and
                      verifies/updates them instead of researching them again.

Both read the same knowledge base (`prep_world.db.recall`, pgvector `kb_chunks`, scoped
to one company). Approved briefs are written back by the approve flow (`db.remember`),
so every approved brief is memory for the next run.
"""
from __future__ import annotations

import asyncio
import re

from operonx.agents.memory import MemoryEntry, MemoryProvider
from operonx.core.ops.transform.func_op import op
from prep_world import db

from prepare import _run_memo

LABEL = "company_memory"
HEADING = ("Known from past meetings and approved briefs with this company. Do not research these "
           "again; verify or update them, and report what is new or changed:")

# How OperonX renders recalled memory (`render_memory_block`; `gather_memory` labels it "memory").
_BLOCK = re.compile(r"^<(memory|company_memory)>\n(.*)\n</\1>$", re.S)

# `ops.research_tasks` words every task "Research <name> for a sales meeting: …".
_TASK = re.compile(r"Research (.+?) for a sales meeting")


class CompanyMemory(MemoryProvider):
    """The knowledge base, scoped to the company the agent was asked about.

    A provider is built once with the graph, but a run is about one company: the
    company is read from the agent's task (the query OperonX passes is the last user
    turn) and looked up in the CRM, so an agent never sees another company's notes.
    An unknown company recalls nothing. Within a run the same question is answered
    once (the loop asks every turn)."""

    bound = "io"
    label = LABEL

    def __init__(self, k: int = 3) -> None:
        self.k = k

    async def _prefetch(self, query: str, limit: int) -> list[MemoryEntry]:
        m = _TASK.search(query)
        if not m:
            return []

        async def look() -> list[MemoryEntry]:
            company = await asyncio.to_thread(db.find_company, m.group(1))
            if not company:
                return []
            found = await asyncio.to_thread(db.recall, query, min(limit, self.k), company["id"])
            return [MemoryEntry(r["content"], f"{company['id']}/{r['source']}", 1.0 - float(r["distance"]))
                    for r in found]

        return await _run_memo.call(("memory", query), look, counted=False)

    async def _write(self, text: str, source: str) -> None:
        # Writes need a company; the approve flow does them (`db.remember`).
        raise NotImplementedError("company memory is written by the approve flow, per approved brief")


@op
def place_memory(messages: list = None) -> dict:
    """Seat the recalled memory right after the system prompt.

    OperonX appends the memory block after the conversation (built for per-query
    memory). Ours is the same every turn of a run — one company, one task — so it
    belongs in the stable prefix: the model reads it as background, not as the newest
    user turn, and the prefix stays cacheable."""
    msgs = [dict(m) for m in messages or [] if isinstance(m, dict)]
    block = next((m for m in reversed(msgs) if m.get("role") == "user" and _BLOCK.match(str(m.get("content") or ""))),
                 None)
    if block is None:
        return {"messages": msgs}
    rest = [m for m in msgs if m is not block]
    body = _BLOCK.match(block["content"]).group(2).strip()
    seat = 0
    while seat < len(rest) and rest[seat].get("role") == "system":
        seat += 1
    return {"messages": rest[:seat] + [{"role": "system", "content": f"{HEADING}\n{body}"}] + rest[seat:]}


@op(bound="io")
async def company_memory(website: list = None, news: list = None, people: list = None) -> dict:
    """What the agents will start from, looked up before they start: the same recall each
    agent's `context → recalled` step makes (same provider, same query, same limit), so
    the agents' first turn finds it in the run memo and the network is asked once. It
    changes nothing an agent sees; it makes the agents' memory a step on the canvas."""
    provider = CompanyMemory()

    async def known(task: list = None) -> list:
        asked = next((m["content"] for m in reversed(task or []) if m.get("role") == "user"), "")
        return [e.text for e in await provider.prefetch(asked, 5)]  # 5: gather_memory's default limit

    website_, news_, people_ = await asyncio.gather(known(website), known(news), known(people))
    return {"website": website_, "news": news_, "people": people_}

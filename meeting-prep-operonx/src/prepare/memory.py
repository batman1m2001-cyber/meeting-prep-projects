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
from prep_world import db

from prepare import _run_memo

LABEL = "company_memory"
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

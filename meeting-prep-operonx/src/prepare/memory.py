"""What the research agents already know: company memory.

Two kinds of memory in this flow, on purpose:

    ops.recall        code picks — the workflow fetches the company's notes once and
                      hands them to the brief.
    company memory    the agents' own — `ops.company_memory` recalls, per research task,
                      what past meetings and approved briefs already say; each agent gets
                      it as its `deps`, and `instructions` seats it in the system prompt,
                      so the agent starts from it and verifies/updates it instead of
                      researching it again.

Both read the same knowledge base (`prep_world.db.recall`, pgvector `kb_chunks`, scoped
to one company). Approved briefs are written back by the approve flow (`db.remember`),
so every approved brief is memory for the next run.
"""
from __future__ import annotations

import asyncio
import re

from prep_world import db

from prepare import _run_memo
from prepare._prompts import RESEARCH

# `ops.research_tasks` words every task "Research <name> for a sales meeting: …".
_TASK = re.compile(r"Research (.+?) for a sales meeting")
K = 3

HEADING = ("Known from past meetings and approved briefs with this company. Do not research these "
           "again; verify or update them, and report what is new or changed:")


async def known(task: str, k: int = K) -> list[str]:
    """What the knowledge base says about the company a task is about.

    The company is read from the task and looked up in the CRM, so an agent never sees
    another company's notes; an unknown company recalls nothing. Within a run the same
    task is answered once."""
    m = _TASK.search(task or "")
    if not m:
        return []

    async def look() -> list[str]:
        company = await asyncio.to_thread(db.find_company, m.group(1))
        if not company:
            return []
        return [r["content"] for r in await asyncio.to_thread(db.recall, task, k, company["id"])]

    return await _run_memo.call(("memory", task), look, counted=False)


def instructions(ctx) -> str:
    """The research agent's system prompt, then its task's company memory (its `deps`).
    The same every turn of a run — one company, one task — so it sits in the stable
    prefix: the model reads it as background, and the prefix stays cacheable."""
    notes = ctx.deps or []
    if not notes:
        return RESEARCH
    return RESEARCH + "\n\n" + HEADING + "\n" + "\n".join(f"- {n}" for n in notes)

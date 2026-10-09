"""One run's memo: the same call, made twice in a run, does its work once.

The three research agents run in parallel and often ask for the same thing — the same
search, the company's home page. Keyed by (tool, normalized arguments), the first call
does the request and every identical call in the same run awaits that one, even if it
arrives while the request is still in flight.

Run-scoped, not global: the memo hangs off the run's OperonX trace (one per run — one
email), so two emails never share an answer and the memo is gone when the run is. The
tools are ops, and each call runs as a nested run with a trace of its own: the memo keys
on the root run's (`trace.root`, operonx >= 1.18.1). Outside a run (no trace) nothing is
memoized.

Hits and misses are counted on the run's trace metadata (`tool_cache`), which the local
trace records — "N calls saved" per run — and logged on every hit.
"""
from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable, Hashable

from operonx.core.loggings import LOGGER
from operonx.core.workflow_trace import _current_trace

_ATTR = "_prep_run_memo"


def _run():
    trace = _current_trace.get()
    return trace.root if trace is not None else None


async def call(key: Hashable, work: Callable[[], Awaitable[Any]], counted: bool = True) -> Any:
    """`work()` once per run per `key`; identical calls share its result."""
    run = _run()
    if run is None:
        return await work()
    memo: dict = run.__dict__.setdefault(_ATTR, {})
    stats = run.metadata.setdefault("tool_cache", {"calls": 0, "hits": 0, "misses": 0}) if counted else None
    task = memo.get(key)
    if task is None:
        task = memo[key] = asyncio.ensure_future(work())
        if stats is not None:
            stats["calls"] += 1
            stats["misses"] += 1
    elif stats is not None:
        stats["calls"] += 1
        stats["hits"] += 1
        LOGGER.info("tool cache: hit %s — %d of %d tool calls saved in run %s",
                    key[0], stats["hits"], stats["calls"], run.trace_id)
    try:
        # shield: one caller being cancelled must not cancel the request the others share
        return await asyncio.shield(task)
    except Exception:
        if memo.get(key) is task:
            memo.pop(key, None)  # a failed request is not remembered; the next caller tries again
        raise

"""The golden emails through the LangGraph build, nothing delivered, scored by the
shared scorer.  uv run python eval.py [--concurrency N]  — exits 1 under 90%."""
from __future__ import annotations

import asyncio
import sys
import time
import uuid

from prep_world.mail import golden_cases
from prep_world.score import score, summary

from prep.graph import GRAPH


async def one(case: dict, gate: asyncio.Semaphore) -> dict:
    async with gate:
        t = time.perf_counter()
        thread = uuid.uuid4().hex
        out = await GRAPH.ainvoke({"email": case["input"], "deliver": False, "thread": thread},
                                  {"configurable": {"thread_id": thread}, "recursion_limit": 50})
        s = score(case["id"], out.get("outcome") or {})
        s["ms"] = (time.perf_counter() - t) * 1000
        return s


async def main() -> int:
    n = int(sys.argv[sys.argv.index("--concurrency") + 1]) if "--concurrency" in sys.argv else 8
    gate = asyncio.Semaphore(n)
    t = time.perf_counter()
    scores = await asyncio.gather(*(one(c, gate) for c in golden_cases()))
    for s in scores:
        bad = [k for k, ok in s["checks"].items() if not ok]
        print(f"{'ok ' if s['passed'] else 'BAD'} {s['id']:<22} {s['ms']:7.0f} ms {bad or ''}")
    res = summary(scores)
    print(res, f"{time.perf_counter() - t:.1f}s")
    return 0 if res["passed"] / res["total"] >= 0.9 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

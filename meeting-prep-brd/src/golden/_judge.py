"""The golden eval's evaluator: the world's shared scorer, unchanged."""
from __future__ import annotations

from prep_world.score import score


def judged(input: dict, output: dict) -> dict:  # noqa: A002 — the evaluator's own argument name
    s = score(input["id"], output or {})
    failed = [k for k, ok in s["checks"].items() if not ok]
    return {"passed": s["passed"], "score": s["completeness"] if s["completeness"] is not None else float(s["passed"]),
            "reason": "ok" if s["passed"] else f"failed: {', '.join(failed)}"}

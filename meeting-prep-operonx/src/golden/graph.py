"""The golden emails, as an eval: each case is one email through `prepare`,
delivering nothing, judged by the shared scorer."""
from operonx import END, START, graph
from operonx.app.serve import egress, ingress
from prep_world.score import score

from golden import ops
from prepare.graph import prepare


@graph
def golden_case():
    src = ingress()
    c = ops.case(item=src["item"])
    p = prepare(email=c["email"], deliver=False)
    out = egress(item=p["outcome"])
    START >> src >> c >> p >> out >> END


def judged(input: dict, output: dict) -> dict:  # noqa: A002 — the evaluator's own argument name
    s = score(input["id"], output or {})
    failed = [k for k, ok in s["checks"].items() if not ok]
    return {"passed": s["passed"], "score": s["completeness"] if s["completeness"] is not None else float(s["passed"]),
            "reason": "ok" if s["passed"] else f"failed: {', '.join(failed)}"}

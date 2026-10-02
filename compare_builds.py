"""Compare the two builds on their golden eval runs, from what they recorded.

    python compare_builds.py                       # the latest golden run of each build
    python compare_builds.py --brd DIR --opt DIR   # given eval run dirs (…/evals/golden/<run_id>)

Each build's `operonx-run golden` writes `evals/golden/<run_id>/{run.json,items.jsonl}`
and one trace per email under `.operonx/runs/evals/golden/<run_id>/<trace_id>/nodes.jsonl`.
Everything below is counted from those files; nothing is estimated except cost.

    score         the eval's pass rate (the shared scorer, prep_world.score), and completeness
    LLM calls     model calls per email: trace nodes of type "llm"
    tool calls    calls to a tool (MCP, web, knowledge base) per email:
                    brd — every `execute` step of the tool harness (node "ran")
                    opt — every agent tool dispatch (node "run") plus its workflow steps that
                          call a tool: identify (1), crm (2: contacts, history), meetings (1), kb (1)
    tokens        prompt + completion tokens per email, from each model call's usage
    latency       p50 / p95 of the per-email wall time the eval recorded
    cost          per 1,000 emails at gpt-4o-mini list prices ($0.15 / 1M input, $0.60 / 1M output),
                  for both builds alike (the optimized build's calls without tools are actually
                  served by the in-house model through the router)
"""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
PRICE_IN, PRICE_OUT = 0.15 / 1e6, 0.60 / 1e6
OPT_TOOL_STEPS = {"run": 1, "identify": 1, "crm": 2, "meetings": 1, "kb": 1}


def latest(project: Path) -> Path:
    runs = sorted((project / "evals" / "golden").glob("*/run.json"))
    if not runs:
        raise SystemExit(f"no golden eval run under {project}/evals/golden")
    return runs[-1].parent


def trace_nodes(project: Path, run_id: str, trace_id: str) -> list[dict]:
    path = project / ".operonx" / "runs" / "evals" / "golden" / run_id / trace_id / "nodes.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def tool_calls(build: str, nodes: list[dict]) -> int:
    if build == "brd":
        return sum(n["op_name"] == "ran" for n in nodes)
    return sum(OPT_TOOL_STEPS.get(n["op_name"], 0) for n in nodes if n["op_type"] == "code")


def pct(values: list[float], q: float) -> float:
    values = sorted(values)
    return values[min(len(values) - 1, round(q * (len(values) - 1)))]


def measure(build: str, run_dir: Path) -> dict:
    project = run_dir.parents[2]
    run = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    items = [json.loads(line) for line in (run_dir / "items.jsonl").read_text(encoding="utf-8").splitlines()]
    per = []
    for item in items:
        nodes = trace_nodes(project, run["run_id"], item["trace_id"])
        llm = [n for n in nodes if n["op_type"] == "llm" and n["status"] == "ok"]
        usage = [(n.get("outputs") or {}).get("usage") or {} for n in llm]
        tin = sum(u.get("prompt_tokens", 0) for u in usage)
        tout = sum(u.get("completion_tokens", 0) for u in usage)
        per.append({"id": item["key"], "ms": item["ms"], "llm": len(llm), "tools": tool_calls(build, nodes),
                    "tokens_in": tin, "tokens_out": tout, "passed": item["verdict"]["passed"],
                    "action": (item["verdict"].get("output") or {}).get("action")})
    briefs = [p for p in per if p["action"] == "brief"]
    mean = statistics.mean
    return {
        "build": build, "run": run["run_id"], "cases": run["eval"]["cases"], "passed": run["eval"]["passed"],
        "pass_rate": run["eval"]["pass_rate"],
        "llm": mean(p["llm"] for p in per), "llm_brief": mean(p["llm"] for p in briefs) if briefs else 0,
        "tools": mean(p["tools"] for p in per), "tools_brief": mean(p["tools"] for p in briefs) if briefs else 0,
        "tokens": mean(p["tokens_in"] + p["tokens_out"] for p in per),
        "tokens_brief": mean(p["tokens_in"] + p["tokens_out"] for p in briefs) if briefs else 0,
        "p50_s": pct([p["ms"] for p in per], 0.5) / 1000, "p95_s": pct([p["ms"] for p in per], 0.95) / 1000,
        "p50_brief_s": pct([p["ms"] for p in briefs], 0.5) / 1000 if briefs else 0,
        "cost_1000": 1000 * mean(p["tokens_in"] * PRICE_IN + p["tokens_out"] * PRICE_OUT for p in per),
        "failed": [p["id"] for p in per if not p["passed"]],
    }


def table(rows: list[dict]) -> str:
    lines = ["| | " + " | ".join(r["build"] for r in rows) + " |", "|---|" + "---|" * len(rows)]
    spec = [
        ("golden score (19 emails)", lambda r: f"{r['passed']}/{r['cases']} ({r['pass_rate']:.0%})"),
        ("LLM calls / email (all · briefs)", lambda r: f"{r['llm']:.1f} · {r['llm_brief']:.1f}"),
        ("tool calls / email (all · briefs)", lambda r: f"{r['tools']:.1f} · {r['tools_brief']:.1f}"),
        ("tokens / email (all · briefs)", lambda r: f"{r['tokens']:,.0f} · {r['tokens_brief']:,.0f}"),
        ("latency p50 / p95 (all)", lambda r: f"{r['p50_s']:.1f} s / {r['p95_s']:.1f} s"),
        ("latency p50 (briefs)", lambda r: f"{r['p50_brief_s']:.1f} s"),
        ("cost / 1,000 emails (gpt-4o-mini prices)", lambda r: f"${r['cost_1000']:.2f}"),
        ("failed cases", lambda r: ", ".join(r["failed"]) or "—"),
        ("eval run", lambda r: f"`{r['run']}`"),
    ]
    return "\n".join(lines + [f"| {name} | " + " | ".join(f(r) for r in rows) + " |" for name, f in spec])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--brd", type=Path, help="eval run dir of meeting-prep-brd (default: its latest)")
    ap.add_argument("--opt", type=Path, help="eval run dir of meeting-prep-operonx (default: its latest)")
    args = ap.parse_args()
    brd = measure("brd", args.brd or latest(HERE / "meeting-prep-brd"))
    opt = measure("opt", args.opt or latest(HERE / "meeting-prep-operonx"))
    brd["build"], opt["build"] = "brief's design (meeting-prep-brd)", "optimized (meeting-prep-operonx)"
    print(table([brd, opt]))


if __name__ == "__main__":
    main()

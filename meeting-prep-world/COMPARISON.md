# The same system, built twice — measured

*2026-10-01. `meeting-prep-operonx` (OperonX 1.12, local branch) vs `meeting-prep-langgraph`
(LangGraph 1.2.12, LangChain 1.4.3). Same world, same prompts, same golden emails, same
scorer, same mock model (≈0.5 s per call). Single machine, Windows.*

## Results

| | OperonX build | LangGraph build |
|---|---|---|
| golden emails passed | **19 / 19** | **19 / 19** |
| golden eval, wall clock | 14.5 s (`operonx-run golden`) | 14.4 s (`eval.py`, 8 at a time) |
| live: email → approval email | 7.6 s | 6.6 s (one run each: noise) |
| code lines (no blanks, comments, docstrings) | 309 | 257 |
| morning schedule (08:00 sweep) | yes — `schedule(at="08:00")` | **no** — needs cron or APScheduler |
| webhook that answers at once | built in — `webhook("/mail")`, traced, 429 under load | hand-written FastAPI + background tasks, untraced, unbounded |
| eval with a record and a gate | built in — `Eval(..., threshold=0.9)`, run record, exit code | hand-written runner |
| approval survives a restart | yes — the draft waits in the database; the link starts a new run | **no** with `InMemorySaver`; needs `langgraph-checkpoint-postgres` (separate package) |
| the graph drawn from the code | OperonX Studio, local | LangGraph Studio / LangSmith (not tried: needs the CLI + an account) |
| engine overhead (`bench/bench_engines.py`) | 2–15× lower | — |

**Reading it honestly:** with the model dominating latency, the two run the same; the
engine's speed shows in batch, streaming and many small steps, not here. The LangGraph code
is shorter because it does less: add a schedule, a bounded traced webhook, an eval record and
durable approval and it grows past the OperonX build. What OperonX buys is the part around
the graph — triggers, evals, traces, Studio — owned by the team.

## What each build ran into

| | OperonX | LangGraph |
|---|---|---|
| bugs found in the engine | **one, real**: an agent nested in a graph lost its question and doubled its messages — fixed in the engine, with tests | none |
| missing pieces added to the engine | `webhook`, `schedule`, `agent["final"]`, `MCPClient.call_value` (same week, PR to 1.12.0) | — (wrote them in the app instead) |
| traps hit in the app | the ingress item is single-consumer (`transient`): fan it out through one op | `interrupt()` re-runs its node from the top on resume: the approval email went out twice until the node was split |
| MCP lists | `call_value` (new) returns the value | the adapter returns it as `artifact["structured_content"]`, wrapped; unwrapped by hand |

## What to say on stage

- Both are workflow engines; both passed. That is the point of the talk, not a contest.
- LangGraph is the better choice for a team that wants the ecosystem and the hosted tools.
- We own OperonX because the part around the graph is where our products live, and we can
  fix the engine the same day — as this demo did, four times.

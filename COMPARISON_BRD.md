# The brief's design vs the optimized build — measured

*Re-measured 2026-10-13, after the brd build's six agents moved onto AgentOp (PR #12):
both builds' `operonx run golden` in real mode, same 19 golden emails, same scorer
(`prep_world.score`), no mail sent. Produced by `python compare_builds.py` from each run's
eval record and traces.*

| | brief's design (meeting-prep-brd) | optimized (meeting-prep-operonx) |
|---|---|---|
| golden score (19 emails) | 16/19 (84%) | 18/19 (95%) |
| LLM calls / email (all · briefs) | 12.0 · 16.5 | 7.7 · 11.0 |
| tool calls / email (all · briefs) | 13.7 · 19.5 | 9.7 · 14.2 |
| tokens / email (all · briefs) | 14,202 · 19,700 | 4,448 · 6,468 |
| latency p50 / p95 (all) | 24.0 s / 28.9 s | 10.4 s / 15.4 s |
| latency p50 (briefs) | 25.3 s | 11.7 s |
| cost / 1,000 emails (gpt-4o-mini prices) | $2.69 | $1.03 |
| failed cases | mekong-attachment, saigonfresh-followup, lotus-it | colleague |
| eval run | `20261013T085130-656795` | `20261013T085518-037777` |

The 2026-10-02 run (the brd build's hand-written agent loops) is within noise of it: brd
16/19, 12.1 · 16.5 LLM calls, 13,390 · 18,538 tokens, $2.52; optimized 18/19, 8.4 · 11.0
calls, 4,659 · 6,506 tokens, $1.08 — the same failed cases on both sides. Moving onto
AgentOp changed what the studio shows (six agent cards, each run an agent's turns and tool
calls), not what the agents do.

**How the 2026-10-13 run reached the model.** The seminar router's OpenAI key had no credit
left, so its OpenAI side was pointed at OpenRouter (`openai/gpt-4o-mini`,
`openai/text-embedding-3-small` — the same models). The brd build called OpenRouter
directly with `openai/gpt-4o-mini` for every call, as its `openai:` model always went to
OpenAI; the optimized build went through the router as before (its calls with tools to
gpt-4o-mini, those without to the in-house model). Run through OpenRouter for *every* call,
the optimized build's triage gets gpt-4o-mini instead of the in-house model and fails 10
of 19 on `contact` coming back as an object — a model difference, not a build one.

- **meeting-prep-brd** — the brief's design: six LLM agents (AgentOp), each with its own
  MCP tools through the 6-step harness, plus Extract Company Name (one LLM call) and Human
  Approval (a person).
- **meeting-prep-operonx** — the optimized build at `origin/main` (bc4461c): one agent
  (web research), the other boxes are workflow steps.

How each number is counted is in `compare_builds.py`'s docstring (it reads AgentOp's model
usage and tool dispatches since 2026-10-13). Cost is priced at gpt-4o-mini rates for both
builds; the optimized build's tool-less calls actually go to the in-house model, so its
real cost is lower still. The two runs ran one after the other.

**Where the brd build loses facts.** Its three failures are all `mentions`: the Web
Research, Calendar and Company Info agents return the facts (visible in the traces), and
the Memory Agent's merge drops some before the Report Agent writes — e.g. the CRM's pilot
history (saigonfresh-followup), the IT manager who actually wrote (lotus-it, where a
remembered earlier email from the COO took its place). Every security case passes in both
builds: the four attack emails are blocked or cleaned, nothing leaks, nothing is sent.

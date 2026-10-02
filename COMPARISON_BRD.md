# The brief's design vs the optimized build — measured

*2026-10-02, both builds' `operonx-run golden` in real mode (gpt-4o-mini through the seminar
router), same 19 golden emails, same scorer (`prep_world.score`), no mail sent.
Produced by `python compare_builds.py` from each run's eval record and traces.*

| | brief's design (meeting-prep-brd) | optimized (meeting-prep-operonx) |
|---|---|---|
| golden score (19 emails) | 16/19 (84%) | 18/19 (95%) |
| LLM calls / email (all · briefs) | 12.1 · 16.5 | 8.4 · 11.0 |
| tool calls / email (all · briefs) | 13.8 · 19.5 | 10.5 · 14.2 |
| tokens / email (all · briefs) | 13,390 · 18,538 | 4,659 · 6,506 |
| latency p50 / p95 (all) | 25.2 s / 35.4 s | 9.6 s / 17.2 s |
| latency p50 (briefs) | 26.6 s | 10.7 s |
| cost / 1,000 emails (gpt-4o-mini prices) | $2.52 | $1.08 |
| failed cases | mekong-attachment, saigonfresh-followup, lotus-it | colleague |
| eval run | `20261002T111029-204604` | `20261002T111245-129598` |

- **meeting-prep-brd** — the brief's design: six LLM agents, each with its own MCP tools
  through the 6-step harness, plus Extract Company Name (one LLM call) and Human Approval
  (a person). Branch `feat/brd-build`.
- **meeting-prep-operonx** — the optimized build at `origin/main` (bc4461c): one agent
  (web research), the other boxes are workflow steps.

How each number is counted is in `compare_builds.py`'s docstring. Cost is priced at
gpt-4o-mini rates for both builds; the optimized build's tool-less calls actually go to the
in-house model, so its real cost is lower still. The optimized run overlapped a one-email
e2e test of the brd build for part of its time.

**Where the brd build loses facts.** Its three failures are all `mentions`: the Web
Research, Calendar and Company Info agents return the facts (visible in the traces), and
the Memory Agent's merge drops some before the Report Agent writes — e.g. the CRM's pilot
history (saigonfresh-followup), the IT manager who actually wrote (lotus-it, where a
remembered earlier email from the COO took its place). Every security case passes in both
builds: the four attack emails are blocked or cleaned, nothing leaks, nothing is sent.

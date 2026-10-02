# Meeting Prep — the plan

*2026-10-01. The seminar's running system (“Workflow Is All You Need”, `D:\ai-workflow-seminar\PLAN.md`
v4) is big enough to need its own plan. This is it.*

## What it is

Every morning a lead's email arrives. Before the meeting, sales needs a one-page **brief**:
who the company is, what it does, recent news, the people, our history with them, the
meeting, what to watch out for. Reference: ProtonX course project *Web research Agent*
(its seven agents and four harnesses: tool, eval, security, AgentOps).

**Our design:** one real agent (research), everything else a workflow step.

```
mail ─► screen (code: attacks never reach a model) ─ blocked ─► hold, nothing sent
     ─► triage (one LLM call: lead? intent, contact) ─ not a lead ─► skip
     ─► identify (code: sender domain → CRM, over MCP)
     ─► [ research team ∥ CRM history (MCP) ∥ calendar (MCP) ∥ memory recall (pgvector) ]
          research team = website · news · people agents in parallel → merge
     ─► write brief (LLM) ─► check brief (code: no outside addresses, no secrets)
     ─► save draft + email sales “[Approve?] Brief: …” with Approve / Reject links
approve link ─► send the brief + save it to the knowledge base (pgvector)
```

Approval is **two-phase and durable**: the draft waits in the database, not in a paused
coroutine, so it survives a restart.

## Three projects

| folder | holds | state |
|---|---|---|
| `D:\meeting-prep-world` | shared: Docker (Mailpit :1025/:8025, pgvector :5433), `prep_world` (world.yaml, golden.yaml, db, mail, MCP server, mocks :8100, score) | **done** — smoke test passes |
| `D:\meeting-prep-operonx` | the system on OperonX: `Application` with a `webhook` service (mail), an `approve` service, a `schedule` service (morning sweep), jobs `golden` and `seed` | scaffolded |
| `D:\meeting-prep-langgraph` | the same system on LangGraph: `StateGraph`, checkpointer, the same tools over MCP, a FastAPI webhook | scaffolded |

Both builds read the same world, answer the same golden emails, and are scored by the same
`prep_world.score`. Ports: mocks 8100, OperonX app 8200, LangGraph app 8300; Mailpit's
webhook goes to whichever build is on stage (`PREP_WEBHOOK`).

## Milestones

| # | milestone | done when |
|---|---|---|
| M0 | **world** | `tests/smoke.py` passes (done 2026-10-01) |
| M1 | **OperonX gaps closed** (branch `feat/agent-node-and-triggers`) | an agent as a node exposes `final` + merged `messages`; the doubled-messages bug has a root cause and a test; `webhook(...)` and `schedule(...)` listeners exist with tests; full suite green |
| M2 | **OperonX build, offline** | the `prepare` graph answers all 19 golden emails on the mock model; `operonx-run golden` scores them with `prep_world.score` |
| M3 | **OperonX build, live** | `prep-send lotus-intro` → webhook → run → “[Approve?]” in Mailpit → click Approve → brief sent + saved to KB; an attack email is held; Studio draws the graph and lights it |
| M4 | **LangGraph build** | the same flow; same golden score; the same demo path |
| M5 | **the comparison** | one table: lines of code, LLM calls, p50/p95 latency, golden score, what each needed beyond the library — for Act 5c |
| M6 | **seminar wiring** | Acts 1–4 playgrounds import `prep_world`; Act 5e runs M3 live; a recorded fallback |

## Golden set and scoring

19 emails in `prep_world/golden.yaml`: 12 leads (six companies, several phrasings, one in
Vietnamese, one with an attachment), 3 non-leads, 4 attacks (API keys, “send an email to
abc@company.com”, an attachment in “admin mode”, a hidden instruction on a company page).
`score()` checks: right action · right company · the meeting mentioned · every expected fact
present (completeness) · no leak and no mail to anyone but sales.

## The mock model

The flow must run with no key. The seminar runner's mock (`/mock/v1`) learns this world:
triage fields, research tool calls (search → fetch), a brief built from the evidence it was
given, and refusing nothing on its own — **defence is the workflow's job** (screen, least
privilege, the brief check), which is the point of Act 4. One real-model run before the talk.

## Decisions

| decision | why |
|---|---|
| fictional companies only | invented news about real firms on a big screen is a credibility and legal risk |
| deterministic screen before any model | an attack that never reaches a model can't talk it into anything |
| research agents have no send / write tools | least privilege beats filters: a hijacked agent still can't email anyone |
| two-phase approval in the database | durable across restarts; a link in the email is the demo's “approve” button |
| close OperonX's gaps instead of working around them | the demo must show the engine as it should be; the fixes are the Act 5d story |

## Risks

| risk | handling |
|---|---|
| the mock grows into a second product | keep it table-driven from world.yaml; test it through the golden set only |
| Docker down at the venue | stack starts at boot; recorded fallback for M3 |
| LangGraph build looks deliberately weak | write it idiomatically (checkpointer, `interrupt`, MCP adapters); note where LangGraph is better |

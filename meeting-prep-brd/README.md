# Meeting Prep — the course brief's design, on OperonX

The meeting-prep assistant built **exactly as the course brief draws it**: every box
of the flow diagram is a node, and every box the diagram calls an agent is an LLM
that reaches the world only through its own tools (MCP servers), each call through
a 6-step tool harness. It sits beside the optimized build (`../meeting-prep-operonx`)
so the talk can compare the two, measured (`../COMPARISON_BRD.md`).

The plan, and the decisions behind it: `../REBUILD_PLAN.md`.

```
prepare_brief(email_id, notify)
  Email Agent ─ customer email ─► Extract Company Name ─► Web Research Agent ─┐
              └ not a customer / attack ─► no_brief     ─► Calendar Agent ─────┼─► Memory Agent ─► Report Agent ─► Human Approval
                                                        ─► Company Info Agent ┘                                    (a person: the run ends)
deliver(approval_id, decision)          — on the approve link
  decide ─ approved ─► Email Agent (send to sales) ∥ save to KB and memory ─► delivered
         └ rejected ─► not_delivered
```

## The diagram, box for box

| diagram box | node in `prepare_brief` / `deliver` | code | what it is | its tools (MCP) |
|---|---|---|---|---|
| Email Inbox → New Customer Email | the `prepare` service door: `POST /prepare {"email_id"}` | `src/doors/` | the trigger (Mailpit's webhook stays with the optimized build on :8200) | — |
| **Email Agent** | `email` | `src/agents/email_agent/` | **agent**: reads and analyses the email; sender, company, content, intent; brief / skip — or **block** when the injection screen withheld it | `mail__list_new` `mail__read` `mail__send` `mail__status` `crm__find_company` |
| Extract Company Name | `extract_company_name` | `src/extract_company/` | a plain step (no loop): one LLM extraction (JSON, checked) → CRM lookup through the harness | `crm__find_company` |
| **Web Research Agent** | `web_research` | `src/agents/web_research_agent/` | **agent**: website, field, products, size, news, people, sources | `web__search` `web__fetch` `web__news` |
| **Calendar Agent** | `calendar` | `src/agents/calendar_agent/` | **agent**: upcoming meetings with the company | `calendar__meetings` `calendar__upcoming` |
| **Company Info Agent** | `company_info` | `src/agents/company_info_agent/` | **agent**: CRM profile, contacts, history; knowledge-base notes | `crm__find_company` `crm__contacts` `crm__history` `kb__search` |
| **Memory Agent** | `memory` | `src/agents/memory_agent/` | **agent**: merges the three results with past memory, de-duplicates, says what is new; remembers facts and the research run | `memory__recall` `memory__history` `memory__user_profile` `memory__remember` |
| **Report Agent** | `report` | `src/agents/report_agent/` | **agent**: the brief's six sections (intro, field, products, recent news, contacts, points to note) as Markdown and as an email | `report__render_markdown` `report__email_body` |
| Human Approval — *"Review and approve the briefing"* | `review` | `src/human_approval/` | **a person**, not an agent: the brief is saved as a pending approval (`brd.approvals`) and sales is emailed it with Approve / Reject links; the run ends | `approval__request`, `mail__send` (to sales, pending approvals only) |
| Send Brief / Save to KB | `deliver` (the `approve` service: `GET /approve?approval=&decision=`) | `src/deliver/` | the person's click → **Email Agent** sends the brief to sales (only with that approved approval) ∥ save to KB and memory | `mail__send` `mail__status` · `kb__save` `memory__remember` |

Six agents, one plain step, one person. Each agent = system prompt (a `.prompt` file) +
its tools (its row in `src/agents/_shared/scopes.yaml`) + a loop until it answers with
its structured output, which its own op checks; a bad answer is an error, never a default.

## How an agent is written

One package per agent: `graph.py` holds one module-level `@graph` that writes the loop
out — the opening messages, the agent's tool schemas, the model (`LLMOp` with those
tools), the reply check, the tool calls fanned out through the harness, the back-edge —
and `ops.py` its task and its answer. Nothing builds an agent from a factory; what
differs between agents is data (prompt, scopes row, output op). What they share lives
once in `src/agents/_shared/`:

```
model ─► reply (checked) ─ done ─► <the agent's answer, checked> ─► END
                          └ tool calls ─► run_tools ─► tool_results ─► count_turn ─► model …
run_tools:  each_call ─► tool_call  (in parallel, one per call)
tool_call:  validate ─► authenticate ─► authorize ─► rate_limit ─► audit ─► execute ─► as_data
```

| harness step | op | what it checks |
|---|---|---|
| 1 validate | `validate` | a known tool; arguments a JSON object matching its schema |
| 2 auth | `authenticate` | the caller is a known identity |
| 3 scopes | `authorize` | its own tools only; mail only to sales, the Email Agent only with an **approved** `approval_id`, Human Approval only about a **pending** one; no outbound text that leaks (keys, attack text, foreign addresses) |
| 4 rate limit | `rate_limit` | per identity and tool, per minute |
| 5 audit | `audit` | every call, allowed or refused, into `brd.audit` |
| 6 execute | `execute` | the MCP call with a timeout; a failure comes back as a value |
| — | `as_data` | injection screen (an attack email is withheld whole; instruction lines elsewhere are dropped) and the result quoted as data: `{tool, ok, data, error}` |

Security, end to end: the screen decides `block`, not the model; tool output is data;
least-privilege scopes; a leak check on every outbound text; nothing is sent before a
person approves.

## Files

| path | holds |
|---|---|
| `app/main.py` | the Application: services `prepare` and `approve` on :8400, the `golden` eval (gate 0.9) |
| `src/prepare_brief/`, `src/deliver/` | the two flows |
| `src/agents/<agent>/` | one agent each: `graph.py`, `ops.py`, `prompts/` |
| `src/agents/_shared/` | the loop's steps and the tool harness (`ops.py`, `graph.py`), MCP pool, scopes |
| `src/extract_company/`, `src/human_approval/` | the two boxes that are not agents |
| `src/tools/` | the eight MCP servers (stdio): mail, crm, calendar, kb, memory, report, approval, web |
| `src/stores/` | the `brd` schema (memory, research runs, user profile, reports, approvals, saved briefs, audit) and its seed |
| `src/doors/`, `src/golden/` | how runs start: the service doors, the eval |
| `tests/repo/test_graph_conventions.py` | the OperonX conventions, from qc-snatcher, over `src/` and `app/` |
| `tests/unit/` | every tool; the harness step by step |
| `tests/e2e/test_service.py` | /prepare → review email → approve link → brief sent to sales, saved (real model; deletes its mail) |

## Run

```bash
cp .env.example .env   # PREP_DB_URL (5434), OPENAI_BASE_URL (the seminar router), OPENAI_API_KEY
set -a; . ./.env; set +a
PYTHONPATH=src uv run python -m stores.seed   # schema brd (idempotent; --reset drops brd only)
uv run pytest -q                        # conventions, tools, harness, e2e (live services; skipped when down)
uv run operonx-run golden               # the 19 golden emails, real model, no mail; fails under 90%
uv run operonx-serve                    # :8400
curl -s localhost:8400/prepare -H 'content-type: application/json' -d '{"email_id": "<a Mailpit id>"}'
```

The world (Postgres + pgvector, Mailpit, the mock web on :8100) is `../meeting-prep-world`;
the model is `gpt-4o-mini` through the seminar router (`resources.yaml`, `llm:agent`).

# Meeting Prep — on OperonX

A lead's email arrives; a brief for sales comes back for approval. One agent (research),
everything else a workflow step. The plan and the shared world: `../meeting-prep-world`.

```
on_mail:  src ─► inbox ─► prepare
prepare:  email ─► extract_company ─► [ web_research ∥ calendar ∥ company_info ]
                ─► memory ─► report ─► human_approval        (the run ends; the link goes on)
approve:  send_or_save ─► the reply
```

## The course brief's diagram, box for box

Each box is a zone: a nested `@graph`, one node in its parent. Collapsed in Studio,
`on_mail` → `prepare` reads like the brief; open a zone to see its steps.

| brief box | zone | what's inside | agent? |
|---|---|---|---|
| Email Inbox → New Customer Email | `inbox` (`src/inbox/graph.py`) | `fetch` the new message whole (Mailpit) → our own mail is `ignore`d; anything else goes on to `prepare` | no — code |
| Email Agent | `email` | `gate` (security screen) → `blocked` · or `read` the letter → `triage` (LLM, structured: is_lead / intent / contact) → not a lead → `skip` · `verdict` | one LLM call, no tools |
| Extract Company Name | `extract_company` | `identify`: CRM find-company by the sender's domain (MCP) | no — code over MCP |
| Web Research Agent (website, news, LinkedIn) | `web_research` | `tasks` → `company_memory` (what the agents will start from) → `website` ∥ `news` ∥ `people`: three ReAct agents, read-only tools, company memory each turn, identical tool calls once per run | **yes — 3 agents** |
| Calendar Agent | `calendar` | `meetings`: calendar meetings with the company (MCP) | no — code over MCP |
| Company Info Agent (DB, CRM, KB) | `company_info` | `crm`: contacts + history (MCP) ∥ `kb`: knowledge-base recall (pgvector) | no — code |
| Memory Agent (merge, dedupe, context) | `memory` | `merge` every source into evidence lines → `dedupe` into one evidence pack | no — code |
| Report Agent | `report` | `brief` (LLM writes the brief from the evidence) → `check` (leaks, unknown company) | one LLM call, no tools |
| Human Approval | `human_approval` | clean → `ask` (save draft, "[Approve?]" email to sales) · leaky → `hold` · `waiting` | a person |
| Send Brief / Save to KB | `send_or_save` (`src/approve/graph.py`, the link's service) | `decide` → `send` the brief to sales → `save` it into the KB (next run's memory) → `reply` | no — code |

The brief draws six "agents"; here only Web Research is an agent (it decides which tools to
call, turn by turn). The others have one fixed path, so they are workflow steps — a zone
named after the box. The research agents' memory is visible twice: `company_memory` before
them in `web_research`, and `context → recalled` inside each agent (same recall, same run
memo, so it is fetched once).

| file | holds |
|---|---|
| `app/main.py` | the services (`mail` webhook, `approve` link, `morning` 08:00 sweep) and the `golden` eval |
| `src/prepare/` | the flow: `graph.py` wiring, `ops.py` steps, `tools.py` the research tools, `_mcp.py` |
| `src/inbox/`, `src/approve/`, `src/golden/` | how runs start and end (`inbox`, `send_or_save` zones) |
| `tests/test_zones.py` | the approve link and the inbox door, offline (mail and drafts faked) |
| `datasets/golden.jsonl` | the 19 golden emails as eval cases |

## Run

```bash
# the world: Mailpit + pgvector (once), the mock web, a model (the seminar runner's mock)
(cd ../meeting-prep-world && docker compose up -d && uv run prep-seed && uv run prep-mocks)
# here
uv run operonx-run golden      # the eval: 19 cases, fails under 90%
uv run python tests/test_zones.py   # approve link + inbox door, nothing sent
uv run operonx-serve           # :8200 — then: (cd ../meeting-prep-world && uv run prep-send lotus-intro)
```

Or the whole stack at once from the seminar repo: `./stack.sh up`. If 5433 is taken, set
`PREP_DB_PORT` (docker) and `PREP_DB_URL` (every process) to another port.

Needs operonx 1.12 (webhook, schedule, `agent["final"]`, `MCPClient.call_value`).

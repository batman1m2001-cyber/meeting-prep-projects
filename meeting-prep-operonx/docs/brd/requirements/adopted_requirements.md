# meeting-prep-operonx: requirements found in the project

Extracted from the project's own docs, code and tests (`operonx-project adopt`, 2026-10-19). The quote is the source's own words, at the location given; the reading is ours. Status is not here: see [`requirements_traceability.md`](requirements_traceability.md).

## Functional requirements

| ID | Location | Quote (source language) | Reading | Doc status |
|---|---|---|---|---|
| MPO-REQ-INBOX-01 | src/inbox/graph.py module docstring | Email Inbox → New Customer Email: read the new message whole; our own mail (the approval requests) is ignored, anything else goes to prepare | Mail sent by our own domain is marked read and stops at the inbox; any other mail goes to prepare. | documented |
| MPO-REQ-INBOX-02 | app/main.py module docstring | mail     webhook  POST /mail       Mailpit's new-mail hook → prepare a brief, ask for approval | A new-mail webhook on POST /mail runs on_mail, which prepares a draft and sends one approval email. | documented |
| MPO-REQ-INBOX-03 | app/main.py module docstring | morning  schedule 08:00            catch up on anything unread | Every day at 08:00 all unread emails are run through prepare. | documented |
| MPO-REQ-EMAIL-01 | README.md, table 'The course brief's diagram' | `gate` (security screen) → `blocked` · or `read` the letter → `triage` (LLM, structured: is_lead / intent / contact) → not a lead → `skip` · `verdict` | An email is security-screened, then triaged by one LLM call. Blocked and non-lead mail stops before research. | documented |
| MPO-REQ-COMPANY-01 | README.md, table row Extract Company Name | `identify`: CRM find-company by the sender's domain (MCP) | The company is identified from the sender's email domain via a CRM lookup over MCP. | documented |
| MPO-REQ-RESEARCH-01 | README.md, table row Web Research Agent | `tasks` → `company_memory` (what the agents will start from) → `website` ∥ `news` ∥ `people`: three ReAct agents, read-only tools, company memory each turn | Three research agents (website, news, people) run in parallel, each starting from company memory. | documented |
| MPO-REQ-CAL-01 | README.md, table row Calendar Agent | `meetings`: calendar meetings with the company (MCP) | Meetings already booked with the company are fetched from the calendar over MCP. | documented |
| MPO-REQ-INFO-01 | README.md, table row Company Info Agent | `crm`: contacts + history (MCP) ∥ `kb`: knowledge-base recall (pgvector) | CRM contacts and history and knowledge-base notes are fetched in parallel. | documented |
| MPO-REQ-MEMORY-01 | README.md, table row Memory Agent | `merge` every source into evidence lines → `dedupe` into one evidence pack | All sources are merged into evidence lines, and each fact appears once in the evidence pack. | documented |
| MPO-REQ-REPORT-01 | README.md, table row Report Agent | `brief` (LLM writes the brief from the evidence) → `check` (leaks, unknown company) | One LLM call writes the brief, then code checks it for leaks and an unknown company. | documented |
| MPO-REQ-APPROVAL-01 | README.md, table row Human Approval | clean → `ask` (save draft, "[Approve?]" email to sales) · leaky → `hold` · `waiting` | A clean brief is saved as a draft and an [Approve?] email goes to sales. A leaky brief is held. | documented |
| MPO-REQ-APPROVAL-02 | src/approve/graph.py, send_brief_or_save docstring | Approve → the brief goes to sales and into memory. Reject → nothing. | Approving a draft sends the brief to sales and saves it to the KB. Rejecting does neither. | documented |
| MPO-REQ-APPROVAL-04 | app/main.py module docstring | approve  http     GET  /approve    the link in the approval email → send the brief, remember it | GET /approve?draft=&decision= is the approval link and replies with {reply: ...}. | documented |

## Non-functional requirements

| ID | Location | Quote (source language) | Reading | Doc status |
|---|---|---|---|---|
| MPO-REQ-RESEARCH-03 | README.md, table row Web Research Agent | identical tool calls once per run | Within one run, identical research tool calls hit the network once, through a per-run memo. | documented |
| MPO-REQ-RESEARCH-04 | src/prepare/graph.py, researcher agent | limits=UsageLimits(turns=4) | Each research agent gets at most four model turns, and the last must answer without tools. | documented |

## Business rules

| ID | Location | Quote (source language) | Reading | Doc status |
|---|---|---|---|---|
| MPO-REQ-EMAIL-02 | tests/repo/test_graph_conventions.py docstring | every structured model call's `error` is checked \| a reply that fails to parse hands on `None` fields, and `None` reads as an answer | Every structured LLMOp call has its parse error checked before its fields are used. | documented |
| MPO-REQ-RESEARCH-02 | src/prepare/graph.py, READ_ONLY comment | Unattended: the agents may read (both tools are read-only); anything else is refused, never asked. | The research agents may only call read-only tools; any other call is denied without asking. | documented |
| MPO-REQ-APPROVAL-03 | tests/test_zones.py, test_send_or_save docstring | a second click and a reject change nothing | A draft is decided once. A repeated click answers 'already decided, or no such draft' and sends nothing more. | documented |
| MPO-REQ-CONV-01 | tests/repo/test_graph_conventions.py docstring | `@graph` / `@op` only at module level \| a nested one is a factory | Graphs and ops are defined only at module level, never inside functions. | documented |
| MPO-REQ-CONV-02 | tests/repo/test_graph_conventions.py docstring | `@graph` only in `graph.py`, `@op` only in `ops.py` | Graphs live in graph.py and ops in ops.py, and a graph.py holds only graphs. | documented |
| MPO-REQ-CONV-03 | tests/repo/test_graph_conventions.py docstring | `Operon(...)` only at an entry point \| an engine is a process concern; library code composes graphs | Only entry points build an Operon engine. | documented |
| MPO-REQ-CONV-04 | tests/repo/test_graph_conventions.py docstring | no `name=` inside a `@graph` body \| operonx names an op after the variable it is assigned to | Ops are named by their variable, never with an explicit name=. | documented |
| MPO-REQ-CONV-05 | tests/repo/test_graph_conventions.py docstring | every `@graph` / `@op` parameter is used \| an unused one is wiring that carries nothing | Every graph and op parameter is read, and graphs use parameters directly rather than PARENT[...]. | documented |
| MPO-REQ-CONV-06 | tests/repo/test_graph_conventions.py docstring | exits end together: one `[a, b, c] >> END`, not a line each | Wiring is written once: exits are grouped and a fan-out that rejoins is one chain. | documented |

## Success metrics

| ID | Location | Quote (source language) | Reading | Doc status |
|---|---|---|---|---|
| MPO-REQ-EVAL-01 | app/main.py module docstring | golden   the 19 golden emails through prepare, nothing delivered; fails under 90% | The 19 golden emails run through prepare without delivery, and the eval fails if the pass rate is under 90%. | documented |

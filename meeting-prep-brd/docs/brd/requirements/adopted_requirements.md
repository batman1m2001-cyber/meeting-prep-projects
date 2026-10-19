# meeting-prep-brd: requirements found in the project

Extracted from the project's own docs, code and tests (`operonx-project adopt`, 2026-10-19). The quote is the source's own words, at the location given; the reading is ours. Status is not here: see [`requirements_traceability.md`](requirements_traceability.md).

## Business requirements

| ID | Location | Quote (source language) | Reading | Doc status |
|---|---|---|---|---|
| MPB-REQ-FLOW-03 | README.md, The diagram, box for box | Human Approval — "Review and approve the briefing" ... a person, not an agent: the brief is saved as a pending approval (brd.approvals) and sales is emailed it with Approve / Reject links; the run ends | Human Approval is a person's gate: it saves a pending approval, mails sales Approve/Reject links, and the run ends. | documented |
| MPB-REQ-AGENT-01 | README.md, The diagram, box for box | Six agents, one plain step, one person. | The six agents are email, web research, calendar, company info, memory and report. Extract Company Name is a plain step and Human Approval is a person. | documented |
| MPB-REQ-DOC-01 | docs/brd/requirements/requirements_traceability.md | The only place where a requirement's implementation status is stated. | The BRD docs keep a requirements traceability matrix that holds each requirement's status. | documented |

## Functional requirements

| ID | Location | Quote (source language) | Reading | Doc status |
|---|---|---|---|---|
| MPB-REQ-FLOW-01 | app/main.py, module docstring | prepare  http POST /prepare {"email_id"}   a new customer email → seven agents → a brief waiting for approval | POST /prepare with an email id runs prepare_brief and leaves a brief pending approval. | documented |
| MPB-REQ-FLOW-02 | app/main.py, module docstring | approve  http GET /approve?approval=&decision=approve\|reject — the Human Approval link → Send Brief / Save to KB | The approve link decides the approval; approval sends the brief to sales and saves it, rejection sends nothing. | documented |
| MPB-REQ-FLOW-04 | README.md, flow diagram | not a customer / attack ─► no_brief | An email that is not from a customer, or is an attack, ends with no brief. | documented |
| MPB-REQ-TOOLS-01 | README.md, Files | the eight MCP servers (stdio): mail, crm, calendar, kb, memory, report, approval, web | Eight stdio MCP servers expose 22 tools, and the servers' catalog is exactly that list. | documented |
| MPB-REQ-TOOLS-02 | tests/unit/test_tools.py | test_crm_finds_a_company_by_domain_and_knows_none_it_has_not_met | The CRM finds a company by domain, lists contacts and history, and returns an empty result for an unknown company. | documented |
| MPB-REQ-TOOLS-03 | tests/unit/test_tools.py | test_calendar_meetings_of_a_company_and_the_week_ahead | The calendar returns a company's meetings and the meetings in the days ahead. | documented |
| MPB-REQ-TOOLS-04 | tests/unit/test_tools.py | test_kb_saves_and_finds_by_meaning | The knowledge base saves notes and finds them by meaning. | documented |
| MPB-REQ-MEM-01 | README.md, The diagram, box for box | Memory Agent: merges the three results with past memory, de-duplicates, says what is new; remembers facts and the research run | Memory stores a fact once (duplicates are not stored), recalls by meaning, keeps research runs as history, rejects unknown kinds, and returns the user profile. | documented |
| MPB-REQ-REPORT-01 | README.md, The diagram, box for box | the brief's six sections (intro, field, products, recent news, contacts, points to note) as Markdown and as an email | The report is rendered with its six sections as Markdown and as a plain-text email body. | documented |
| MPB-REQ-WEB-01 | README.md, The diagram, box for box | Web Research Agent: website, field, products, size, news, people, sources | Web tools search, fetch only allowed pages, and return news newest-first with a freshness flag. | documented |
| MPB-REQ-MAIL-01 | README.md, The diagram, box for box | Email Agent ... mail__list_new mail__read mail__send mail__status | Mail reads a golden email without a mail server, sends to sales, and tracks delivery. | documented |
| MPB-REQ-AGENT-05 | AGENTOP_PLAN.md, What changes 2 | harness_tools(identity) builds one tool per scoped tool (scopes.yaml) ... A live test checks they equal what the running servers list. | The tools an agent is shown equal the tools the running MCP servers list. | documented |

## Non-functional requirements

| ID | Location | Quote (source language) | Reading | Doc status |
|---|---|---|---|---|
| MPB-REQ-AGENT-04 | AGENTOP_PLAN.md, What stays | Parallel calls: a turn's tool calls still run in parallel. | The tool calls of one turn run in parallel. | documented |
| MPB-REQ-CONV-01 | tests/repo/test_graph_conventions.py, docstring table | @graph / @op only at module level \| a nested one is a factory | Graphs and ops are defined at module level only, never inside a function. | documented |
| MPB-REQ-CONV-02 | tests/repo/test_graph_conventions.py, docstring table | @graph only in graph.py, @op only in ops.py | Each package puts its graphs in graph.py and its ops in ops.py. | documented |
| MPB-REQ-CONV-03 | tests/repo/test_graph_conventions.py, docstring table | Operon(...) only at an entry point | Library code never builds an engine; only an entry point does. | documented |
| MPB-REQ-CONV-04 | tests/repo/test_graph_conventions.py, docstring table | every structured model call's error is checked (parsed) | Every structured LLM call has its error checked, so an unparseable reply never becomes a verdict. | documented |
| MPB-REQ-CONV-05 | tests/repo/test_graph_conventions.py, docstring table | a @graph uses its parameters, never PARENT["param"]; every parameter is used; no name= inside a @graph body; wiring is written once | Graph wiring follows the OperonX style rules. | documented |

## Business rules

| ID | Location | Quote (source language) | Reading | Doc status |
|---|---|---|---|---|
| MPB-REQ-AGENT-02 | README.md, The diagram, box for box | each agent ... a loop until it answers with its structured output, which its own op checks; a bad answer is an error, never a default. | An agent's final answer is checked, and a bad or missing answer raises an error. | documented |
| MPB-REQ-AGENT-03 | AGENTOP_PLAN.md, What stays | Turn limits: the same per agent. On the last turn the model must answer. | Each agent has a turn limit, and on the last turn it must answer. | documented |
| MPB-REQ-HARN-01 | README.md, harness step table | 1 validate \| validate \| a known tool; arguments a JSON object matching its schema | The harness refuses an unknown tool or bad arguments and returns the refusal as a value. | documented |
| MPB-REQ-HARN-02 | README.md, harness step table | 2 auth \| authenticate \| the caller is a known identity | A call from an unknown identity is refused and audited. | documented |
| MPB-REQ-HARN-03 | README.md, harness step table; src/agents/_shared/scopes.yaml, header (Least privilege) | 3 scopes \| authorize \| its own tools only | An agent can call only the tools listed for it in scopes.yaml. | documented |
| MPB-REQ-HARN-04 | README.md, harness step table | mail only to sales, the Email Agent only with an approved approval_id, Human Approval only about a pending one | mail__send goes only to the sales address. The Email Agent needs an approved approval id, and Human Approval may mail only about a pending approval. | documented |
| MPB-REQ-HARN-05 | README.md, harness step table | no outbound text that leaks (keys, attack text, foreign addresses) | Outbound mail and approval requests are refused when the text leaks keys, attack text or outside addresses. | documented |
| MPB-REQ-HARN-06 | README.md, harness step table | 4 rate limit \| rate_limit \| per identity and tool, per minute | Calls are limited per identity and tool per minute. | documented |
| MPB-REQ-HARN-07 | README.md, harness step table | 5 audit \| audit \| every call, allowed or refused, into brd.audit | Every tool call, allowed or refused, is recorded in brd.audit. | documented |
| MPB-REQ-HARN-08 | README.md, harness step table | 6 execute \| execute \| the MCP call with a timeout; a failure comes back as a value | A failing tool returns an error value and does not raise an exception. | documented |
| MPB-REQ-SEC-01 | README.md, harness step table (as_data) | injection screen (an attack email is withheld whole; instruction lines elsewhere are dropped) and the result quoted as data | An attack email is withheld whole and raises an alert. Injected instruction lines are dropped, and the email is still read. | documented |
| MPB-REQ-SEC-02 | README.md, Security, end to end | the screen decides block, not the model; tool output is data; least-privilege scopes; a leak check on every outbound text; nothing is sent before a person approves. | Block decisions come from the screen, and nothing is sent before approval. | documented |

## Success metrics

| ID | Location | Quote (source language) | Reading | Doc status |
|---|---|---|---|---|
| MPB-REQ-EVAL-01 | app/main.py, module docstring | golden   the 19 golden emails through prepare_brief, nothing sent; fails under 90% | The golden eval runs the 19 emails with nothing sent and fails under a 0.9 score. | documented |

# The brd build's agents on AgentOp

**Status (2026-10-13):** A0, A1, A2 and A4 are done; A3 is done except the real-model golden run, which is blocked (see below). Branch `feat/brd-agentop`.

## Why

The brief's six agents each write their loop out by hand: model → `reply` → `run_tools` → back to the model, as their own `@graph`.

When this build was made there was no agent op in OperonX. Its conventions forbid building graphs in a factory, so each agent spelled the loop out (`REBUILD_PLAN.md` §6, Q2).

`AgentOp` has existed since operonx-agents 0.1 (6 Oct), and the optimized build has used it since that day. The brd build never moved. So the studio shows its agents as plain subgraphs: no agent card, and no turns or tool calls read as an agent's.

## What stays

- **The brief's design:** six agents, each with its own tools and its own prompt (`prompts/`). Extract Company Name and Human Approval are not agents.
- **The tool harness:** every tool call still goes through `tool_call`, in the same six steps plus `as_data`:
  - validate, authenticate, authorize, rate limit, audit, execute;
  - then `as_data`: the injection screen, with the result quoted as data.
  - The model reads the same envelope, `{tool, ok, data, error}`.
- **The answer checks:** each agent's last step (`meetings`, `email_facts`, `sent`, `report`, …) still checks the answer against what the tools returned, never against the model's say-so.
- **Turn limits:** the same per agent. On the last turn the model must answer.
- **Parallel calls:** a turn's tool calls still run in parallel.

## What changes

1. **Each agent is an `Agent` spec.**
   - Its fields: `instructions=PROMPTS[name]`, `model=Model("agent")`, `limits=UsageLimits(turns=N)`, and its tools.
   - Its graph is `opening → AgentOp.of(agent=…, input=…) → its answer step`.
   - These go: `count_turn`, `reply`, `tool_results`, `tool_schemas`, and the `PARENT` cells for messages, alerts, tools and turns.
2. **Its tools are the harness.**
   - `harness_tools(identity)` builds one tool per scoped tool (`scopes.yaml`). Each is named and described as the MCP server describes it, with that tool's schema.
   - The schemas are read from the in-repo servers (`src/tools/*.py`) when the module loads, because an agent's tools must exist when its graph is defined. A live test checks they equal what the running servers list.
   - A call runs the `tool_call` graph (`invoke`), so the trace shows `tool call → tool_call → validate … as_data` under the agent's turn.
   - The tool hands the raw arguments to the harness. Its step 1 validates them, so a bad call is still audited.
3. **The transcript.** The answer steps that check what the tools did (`email_facts`, `sent`, `report`) read the run's conversation. AgentOp gains a `messages` output: `RunResult.messages`, the conversation the model last saw. This ships upstream as **operonx-agents 0.2.1**.
4. **The screen's alerts.**
   - `as_data`'s alert (an attack withheld, or lines cleaned) must reach the answer step: an attack decides `block`.
   - It is never put back in front of the model, because its `match` is the attack's own text.
   - The harness tool files it under the agent run's id (`RunContext.run_id`). The answer step takes the run's alerts by AgentOp's `state_id` (`_shared/_screens.py`).
5. **Versions:** operonx 1.16 → 1.22.4, and operonx-agents 0.1.1 → 0.2.1.

## Known differences

- **Unparseable arguments:** a tool call whose arguments are not even a JSON object is refused by AgentOp's dispatch before the harness, so it is not audited. Before, it reached step 1, which refused it and audited it. A model rarely sends non-JSON arguments; this is recorded here rather than worked around.
- **Cut-off or empty replies:** `reply` raised on these. Now they surface as the run's `status` and `error`, and the answer step raises when the run did not complete.

## Phases

- **A0, upstream:** AgentOp's `messages` output, with a test, released as operonx-agents 0.2.1.
- **A1:**
  - `harness_tools` and `_screens`.
  - The Calendar Agent on AgentOp.
  - One golden email end to end.
- **A2:**
  - The other five agents, plus the Email Agent's send task.
  - The loop ops that nothing calls any more are removed.
- **A3, retest:**
  - The conventions, unit and harness tests.
  - The e2e test.
  - `operonx-run golden` in real mode (19 emails, gpt-4o-mini), which must score at least the 16/19 measured before.
  - The optimized build's golden run, then `COMPARISON_BRD.md` re-measured with `compare_builds.py`.
- **A4:** in the studio, the six agents' cards and one run's agents, turns and tool calls (screenshots).

## Where it stands

- **A0:** operonx-agents 0.2.1 is on PyPI with AgentOp's `messages` output (Operonx #152).
- **A1, A2:** all seven agent graphs are on AgentOp; the loop ops are gone.
- **A3, the tests:**
  - Conventions, tools and harness pass, along with the new `tests/unit/test_agents.py` (scripted model, live MCP servers). 509 passed, plus the earlier 528 from the unit run.
  - The 3 tests that fail are the kb and memory tools' embedding calls, refused by OpenAI (`insufficient_quota`).
  - The new tests show:
    - the tools the agents are shown equal the running servers' list;
    - a call runs and audits the harness;
    - an attack the agent read makes the email `block`, while the attack's words never reach the model;
    - a run that did not answer is an error.
- **A3, the golden run is blocked:**
  - The model router's OpenAI key has no credit left. gpt-4o-mini and the embeddings answer `429 insufficient_quota`.
  - The in-house model (`inhouse:`) answers, but its vLLM server has tool calling off (`"auto" tool choice requires --enable-auto-tool-choice`), so no agent can run on it.
  - Once there is credit: `operonx run golden` here and in meeting-prep-operonx, then `python compare_builds.py`. The score must be at least 16/19.
- **A4:** in the studio, the six agents draw as agent cards (email, web, calendar, info, memory, writer). A scripted Calendar Agent run reads `calendar → turn → model, calendar__meetings → tool_call → checked … data`.

The world (mail, db, the web mocks, the model router) is started piece by piece from `ai-workflow-seminar/stack.sh`'s commands for the retest, and stopped after it.

# Meeting Prep — on OperonX

A lead's email arrives; a brief for sales comes back for approval. One agent (research),
everything else a workflow step. The plan and the shared world: `../meeting-prep-world`.

```
mail ─► screen ─► triage (LLM) ─► identify (CRM over MCP)
     ─► [ research: website · news · people agents ∥ CRM ∥ calendar ∥ memory ]
     ─► brief (LLM) ─► check ─► draft + "[Approve?]" email ─► link ─► send + remember
```

| file | holds |
|---|---|
| `app/main.py` | the services (`mail` webhook, `approve` link, `morning` 08:00 sweep) and the `golden` eval |
| `src/prepare/` | the flow: `graph.py` wiring, `ops.py` steps, `tools.py` the research tools, `_mcp.py` |
| `src/inbox/`, `src/approve/`, `src/golden/` | how runs start and end |
| `datasets/golden.jsonl` | the 19 golden emails as eval cases |

## Run

```powershell
# the world: Mailpit + pgvector (once), the mock web, a model (the seminar runner's mock)
cd ..\meeting-prep-world; docker compose up -d; uv run prep-seed; uv run prep-mocks
# here
uv run operonx-run golden      # the eval: 19 cases, fails under 90%
uv run operonx-serve           # :8200 — then: cd ..\meeting-prep-world; uv run prep-send lotus-intro
```

Needs operonx 1.12 (webhook, schedule, `agent["final"]`, `MCPClient.call_value`).

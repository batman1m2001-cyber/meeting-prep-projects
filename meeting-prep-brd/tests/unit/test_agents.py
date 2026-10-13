"""The agents on AgentOp, with a scripted model over the live MCP servers: the
tools they are shown are the servers' own, every call runs the six-step
harness and is audited, and the injection screen's finding reaches the answer
step without reaching the model."""
import asyncio
import json

import pytest
from operonx import Operon
from operonx.agents.testing import ScriptedLLM, asks, says, scripted

from agents._shared import _mcp
from agents._shared.ops import answered
from agents._shared.tools import catalog
from agents.calendar_agent.graph import calendar_agent
from agents.email_agent.graph import email_agent
from stores import brd
from tools._golden import email_id

pytestmark = pytest.mark.live(5434, 8000, 8100)

LOTUS = {"company_id": "lotus", "company_name": "Lotus Logistics", "domain": "lotus-logistics.example"}


def last_audit() -> dict:
    return brd.rows("SELECT agent, tool, verdict FROM brd.audit ORDER BY id DESC LIMIT 1")[0]


def test_the_tools_an_agent_is_shown_are_what_the_running_servers_list():
    live = asyncio.run(_mcp.catalog())
    assert catalog().keys() == live.keys()
    for name, tool in catalog().items():
        assert (tool["description"], tool["schema"]) == (live[name]["description"], live[name]["schema"]), name


def test_an_agents_tool_call_runs_the_harness_and_is_audited():
    model = ScriptedLLM(asks(("calendar__meetings", {"company_id": "lotus"})),
                        says('{"meetings": [{"title": "Port services review"}]}'))
    async def go():
        handle = Operon(calendar_agent, params={"company": None}).start({"company": LOTUS})
        return handle, await handle.result()

    with scripted(agent=model):
        handle, out = asyncio.run(go())
    assert "$errors" not in out, out.get("$errors")
    assert out["meetings"] == [{"title": "Port services review"}] and out["screened"] == []
    assert last_audit() == {"agent": "calendar_agent", "tool": "calendar__meetings", "verdict": "allowed"}
    # the tool's call is the harness, step by step, under the agent's turn
    names = {n.op_name for n in handle.trace.nodes}
    # (steps are named by their variables in `graph.tool_call`: validate → `checked`, …, as_data → `data`)
    assert {"calendar", "turn", "calendar__meetings", "tool_call", "checked", "who", "allowed", "limited",
            "logged", "ran", "data"} <= names, names
    # the model read the harness's envelope
    (tool_msg,) = [m for m in model.requests[-1]["messages"] if m.get("role") == "tool"]
    assert json.loads(tool_msg["content"])["tool"] == "calendar__meetings"


def test_an_attack_the_agent_read_blocks_the_email_and_never_reaches_the_model():
    attack = email_id("attack-keys")
    model = ScriptedLLM(asks(("mail__read", {"email_id": attack})),
                        says(json.dumps({"sender": "x", "sender_email": "x@y", "company_hint": None, "domain": "y",
                                         "content_summary": "", "intent": "", "is_customer_or_partner": True,
                                         "is_new_customer": False, "attachments": []})))
    with scripted(agent=model):
        out = asyncio.run(Operon(email_agent, params={"email_id": None}).run({"email_id": attack}))
    assert "$errors" not in out, out.get("$errors")
    assert out["action"] == "block" and out["screened"][0]["kind"] == "attack"
    # the screen's match (the attack's own words) is in the result, never in what the model read
    match = out["screened"][0]["match"]
    assert match and match not in json.dumps(model.requests[-1]["messages"], ensure_ascii=False)


def test_a_run_that_did_not_answer_is_an_error():
    with pytest.raises(ValueError, match="did not answer"):
        answered.__wrapped__(output=None, status="limit", error=None, state_id="r-1", messages=[])
    with pytest.raises(ValueError, match="empty"):
        answered.__wrapped__(output="  ", status="completed", error=None, state_id="r-2", messages=[])

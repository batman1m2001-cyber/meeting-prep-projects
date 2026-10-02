"""Company Info Agent: an LLM with the CRM and knowledge-base tools, in a
loop — model → tool calls through the harness → model — until it answers."""
import operator

from operonx import END, PARENT, START, graph
from operonx.core.ops import if_
from operonx.providers.ops import LLMOp
from operonx.reducers import add_messages

from .._shared.graph import run_tools
from .._shared.ops import count_turn, reply, tool_results, tool_schemas
from .ops import company_info, opening


@graph
def company_info_agent(company):
    """Company → {profile, contacts, history, kb_notes}."""
    PARENT.declare(messages=[], alerts=[], tools=[], turns=0,
                   reducers={"messages": add_messages, "alerts": operator.add})
    task = opening(company=company)
    schemas = tool_schemas(agent="company_info_agent")
    task["messages"] >> PARENT["messages"]
    schemas["tools"] >> PARENT["tools"]
    turn = count_turn(turns=PARENT["turns"], max_turns=6)
    turn["turns"] >> PARENT["turns"]
    model = LLMOp.of(resource="agent", messages=PARENT["messages"], tools=PARENT["tools"],
                     tool_choice=turn["tool_choice"])
    said = reply(content=model["content"], tool_calls=model["tool_calls"], finish_reason=model["finish_reason"])
    said["messages"] >> PARENT["messages"]
    tools = run_tools(agent="company_info_agent", tool_calls=said["tool_calls"])
    results = tool_results(messages=tools["message"].collect(), alerts=tools["alert"].collect())
    results["messages"] >> PARENT["messages"]
    results["alerts"] >> PARENT["alerts"]
    found = company_info(content=said["content"], alerts=PARENT["alerts"])
    START >> [task, schemas] >> turn >> model >> said >> if_(said["done"] == True, found).else_(tools)  # noqa: E712
    tools >> results >> turn
    found >> END

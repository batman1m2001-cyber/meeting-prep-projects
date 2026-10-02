"""Web Research Agent: an LLM with the web tools (search, fetch, news), in a
loop — model → tool calls through the harness → model — until it answers."""
import operator

from operonx import END, PARENT, START, graph
from operonx.core.ops import if_
from operonx.providers.ops import LLMOp
from operonx.reducers import add_messages

from .._shared.graph import run_tools
from .._shared.ops import count_turn, reply, tool_results, tool_schemas
from .ops import opening, research


@graph
def web_research_agent(company):
    """Company → {website, field, products, size, headquarters, news, people, sources}."""
    PARENT.declare(messages=[], alerts=[], tools=[], turns=0,
                   reducers={"messages": add_messages, "alerts": operator.add})
    task = opening(company=company)
    schemas = tool_schemas(agent="web_research_agent")
    task["messages"] >> PARENT["messages"]
    schemas["tools"] >> PARENT["tools"]
    turn = count_turn(turns=PARENT["turns"], max_turns=8)
    turn["turns"] >> PARENT["turns"]
    model = LLMOp.of(resource="agent", messages=PARENT["messages"], tools=PARENT["tools"],
                     tool_choice=turn["tool_choice"])
    said = reply(content=model["content"], tool_calls=model["tool_calls"], finish_reason=model["finish_reason"])
    said["messages"] >> PARENT["messages"]
    tools = run_tools(agent="web_research_agent", tool_calls=said["tool_calls"])
    results = tool_results(messages=tools["message"].collect(), alerts=tools["alert"].collect())
    results["messages"] >> PARENT["messages"]
    results["alerts"] >> PARENT["alerts"]
    found = research(content=said["content"], alerts=PARENT["alerts"])
    START >> [task, schemas] >> turn >> model >> said >> if_(said["done"] == True, found).else_(tools)  # noqa: E712
    tools >> results >> turn
    found >> END

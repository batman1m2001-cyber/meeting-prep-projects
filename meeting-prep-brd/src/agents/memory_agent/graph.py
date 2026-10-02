"""Memory Agent: an LLM with the memory tools, in a loop — model → tool
calls through the harness → model — until it answers. It merges the three
agents' findings with what was remembered, and remembers what is new."""
import operator

from operonx import END, PARENT, START, graph
from operonx.core.ops import if_
from operonx.providers.ops import LLMOp
from operonx.reducers import add_messages

from .._shared.graph import run_tools
from .._shared.ops import count_turn, reply, tool_results, tool_schemas
from .ops import context, opening


@graph
def memory_agent(company, facts, research, meetings, info):
    """The findings + past memory → {context, new_since_last, profile}; writes the research history."""
    PARENT.declare(messages=[], alerts=[], tools=[], turns=0,
                   reducers={"messages": add_messages, "alerts": operator.add})
    task = opening(company=company, facts=facts, research=research, meetings=meetings, info=info)
    schemas = tool_schemas(agent="memory_agent")
    task["messages"] >> PARENT["messages"]
    schemas["tools"] >> PARENT["tools"]
    turn = count_turn(turns=PARENT["turns"], max_turns=8)
    turn["turns"] >> PARENT["turns"]
    model = LLMOp.of(resource="agent", messages=PARENT["messages"], tools=PARENT["tools"],
                     tool_choice=turn["tool_choice"])
    said = reply(content=model["content"], tool_calls=model["tool_calls"], finish_reason=model["finish_reason"])
    said["messages"] >> PARENT["messages"]
    tools = run_tools(agent="memory_agent", tool_calls=said["tool_calls"])
    results = tool_results(messages=tools["message"].collect(), alerts=tools["alert"].collect())
    results["messages"] >> PARENT["messages"]
    results["alerts"] >> PARENT["alerts"]
    merged = context(content=said["content"], alerts=PARENT["alerts"])
    START >> [task, schemas] >> turn >> model >> said >> if_(said["done"] == True, merged).else_(tools)  # noqa: E712
    tools >> results >> turn
    merged >> END

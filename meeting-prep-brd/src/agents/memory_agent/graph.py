"""Memory Agent: an LLM with the memory tools (AgentOp: model → tool calls
through the harness → model, until it answers). It merges the three agents'
findings with what was remembered, and remembers what is new."""
from operonx import END, START, graph
from operonx.agents import AgentOp

from .._shared.ops import answered
from .._shared.tools import agent
from .ops import context, opening

MEMORY_AGENT = agent("memory_agent", turns=8)


@graph
def memory_agent(company, facts, research, meetings, info):
    """The findings + past memory → {context, new_since_last, profile}; writes the research history."""
    task = opening(company=company, facts=facts, research=research, meetings=meetings, info=info)
    memory = AgentOp.of(agent=MEMORY_AGENT, input=task["input"])
    run = answered(output=memory["output"], status=memory["status"], error=memory["error"],
                   state_id=memory["state_id"], messages=memory["messages"])
    merged = context(content=run["content"], alerts=run["alerts"])
    START >> task >> memory >> run >> merged >> END

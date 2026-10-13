"""Web Research Agent: an LLM with the web tools — search, fetch, news —
(AgentOp: model → tool calls through the harness → model, until it answers),
and its answer checked."""
from operonx import END, START, graph
from operonx.agents import AgentOp

from .._shared.ops import answered
from .._shared.tools import agent
from .ops import opening, research

WEB_RESEARCH_AGENT = agent("web_research_agent", turns=8)


@graph
def web_research_agent(company):
    """Company → {website, field, products, size, headquarters, news, people, sources}."""
    task = opening(company=company)
    web = AgentOp.of(agent=WEB_RESEARCH_AGENT, input=task["input"])
    run = answered(output=web["output"], status=web["status"], error=web["error"],
                   state_id=web["state_id"], messages=web["messages"])
    found = research(content=run["content"], alerts=run["alerts"])
    START >> task >> web >> run >> found >> END

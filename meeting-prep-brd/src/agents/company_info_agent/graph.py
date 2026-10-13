"""Company Info Agent: an LLM with the CRM and knowledge-base tools (AgentOp:
model → tool calls through the harness → model, until it answers), and its
answer checked."""
from operonx import END, START, graph
from operonx.agents import AgentOp

from .._shared.ops import answered
from .._shared.tools import agent
from .ops import company_info, opening

COMPANY_INFO_AGENT = agent("company_info_agent", turns=6)


@graph
def company_info_agent(company):
    """Company → {profile, contacts, history, kb_notes}."""
    task = opening(company=company)
    info = AgentOp.of(agent=COMPANY_INFO_AGENT, input=task["input"])
    run = answered(output=info["output"], status=info["status"], error=info["error"],
                   state_id=info["state_id"], messages=info["messages"])
    found = company_info(content=run["content"], alerts=run["alerts"])
    START >> task >> info >> run >> found >> END

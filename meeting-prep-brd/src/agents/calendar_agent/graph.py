"""Calendar Agent: an LLM with the calendar tools (AgentOp: model → tool calls
through the harness → model, until it answers), and its answer checked."""
from operonx import END, START, graph
from operonx.agents import AgentOp

from .._shared.ops import answered
from .._shared.tools import agent
from .ops import meetings, opening

CALENDAR_AGENT = agent("calendar_agent", turns=5)


@graph
def calendar_agent(company):
    """Company → {meetings: [{title, starts_at, attendees}]}."""
    task = opening(company=company)
    calendar = AgentOp.of(agent=CALENDAR_AGENT, input=task["input"])
    run = answered(output=calendar["output"], status=calendar["status"], error=calendar["error"],
                   state_id=calendar["state_id"], messages=calendar["messages"])
    found = meetings(content=run["content"], alerts=run["alerts"])
    START >> task >> calendar >> run >> found >> END

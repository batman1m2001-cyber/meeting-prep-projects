"""Report Generation Agent: an LLM with the report tools (AgentOp: model →
tool calls through the harness → model, until it answers), and the report
taken from what its tools rendered."""
from operonx import END, START, graph
from operonx.agents import AgentOp

from .._shared.ops import answered
from .._shared.tools import agent
from .ops import opening, report

REPORT_AGENT = agent("report_agent", turns=5)


@graph
def report_agent(company, facts, context, profile):
    """The merged context → the brief {report_id, markdown, subject, email_body}."""
    task = opening(company=company, facts=facts, context=context, profile=profile)
    writer = AgentOp.of(agent=REPORT_AGENT, input=task["input"])
    run = answered(output=writer["output"], status=writer["status"], error=writer["error"],
                   state_id=writer["state_id"], messages=writer["messages"])
    brief = report(company=company, content=run["content"], messages=run["messages"], alerts=run["alerts"])
    START >> task >> writer >> run >> brief >> END

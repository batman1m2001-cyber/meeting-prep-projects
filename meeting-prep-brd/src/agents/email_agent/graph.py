"""Email Agent: an LLM with the mail tools (and the CRM, to tell a new
customer), run by AgentOp — model → tool calls through the harness → model,
until it answers — and its answer checked against what the tools returned.

    email_agent        task "analyse": a new email → its facts, and brief / skip / block
    email_agent_send   task "send": an approved brief → sent to sales, its status
"""
from operonx import END, START, graph
from operonx.agents import AgentOp, UsageLimits

from .._shared.ops import answered
from .._shared.tools import agent
from .ops import email_facts, opening, send_opening, sent

EMAIL_AGENT = agent("email_agent", turns=6)
# the same agent on its other task: fewer turns, a send needs few
EMAIL_SENDER = EMAIL_AGENT.clone(limits=UsageLimits(turns=4))


@graph
def email_agent(email_id):
    """Reads the new email, extracts sender, company and content, says if it is a customer's."""
    task = opening(email_id=email_id)
    email = AgentOp.of(agent=EMAIL_AGENT, input=task["input"])
    run = answered(output=email["output"], status=email["status"], error=email["error"],
                   state_id=email["state_id"], messages=email["messages"])
    facts = email_facts(email_id=email_id, content=run["content"], messages=run["messages"], alerts=run["alerts"])
    START >> task >> email >> run >> facts >> END


@graph
def email_agent_send(approval_id, to, subject, body):
    """Sends an approved brief to the named recipient and tracks its status."""
    task = send_opening(approval_id=approval_id, to=to, subject=subject, body=body)
    send = AgentOp.of(agent=EMAIL_SENDER, input=task["input"])
    run = answered(output=send["output"], status=send["status"], error=send["error"],
                   state_id=send["state_id"], messages=send["messages"])
    done = sent(content=run["content"], messages=run["messages"], alerts=run["alerts"])
    START >> task >> send >> run >> done >> END

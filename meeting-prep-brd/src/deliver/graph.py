"""deliver(approval_id, decision): the diagram's last box, on the approval link.

    decide ─ approved ─► approved_brief ─► Email Agent (send) ─► save_calls ─► save_to_kb ─► delivered
           └ rejected / decided before ─► not_delivered

Send, then save, in one line: `delivered` gathers the two saves with `.collect()`,
and in OperonX 1.12.1 an op after a collect runs in the collect's own context, so
it never meets an input from a branch that ran beside the collect. In a line,
every other input comes from upstream of it.
"""
from operonx import END, START, graph
from operonx.core.ops import if_

from agents._shared.graph import run_tools
from agents.email_agent.graph import email_agent_send

from .ops import approved_brief, decide, delivered, not_delivered, save_calls


@graph
def deliver(approval_id, decision):
    """Send Brief / Save to KB: approved → the Email Agent sends it to sales, and it is saved."""
    decided = decide(approval_id=approval_id, decision=decision)
    brief = approved_brief(report_id=decided["report_id"])
    send_brief = email_agent_send(approval_id=approval_id, to=brief["to"], subject=brief["subject"],
                                  body=brief["body"])
    saving = save_calls(report=brief["report"], approval_id=approval_id)
    save_to_kb = run_tools(agent="deliver", tool_calls=saving["tool_calls"])
    outcome = delivered(approval_id=approval_id, message_id=send_brief["message_id"], status=send_brief["status"],
                        ok=save_to_kb["ok"].collect(), error=save_to_kb["error"].collect())
    refused = not_delivered(approval_id=approval_id, status=decided["status"])
    START >> decided >> if_(decided["approved"] == True, brief).else_(refused)  # noqa: E712
    brief >> send_brief >> saving >> save_to_kb >> outcome
    [outcome, refused] >> END

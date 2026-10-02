"""Human Approval — the diagram's "Review and approve the briefing": a person,
not an agent. No model runs here.

    approval_call ─► request (approval__request, through the harness)
        ├ refused (the brief leaks) ─► held
        ├ notify ─► review_call ─► notify_sales (mail__send to sales, through the harness) ─► waiting
        └ else (the eval: no mail) ─────────────────────────────────────────────────────────► waiting
"""
from operonx import END, START, graph
from operonx.core.ops import if_

from agents._shared.graph import tool_call

from .ops import approval_call, held, review_call, waiting


@graph
def human_approval(report, notify):
    """The brief → a pending approval (sales emailed the links when `notify`), or held."""
    asking = approval_call(report=report)
    request = tool_call(agent="human_approval", call=asking["call"])
    review = review_call(report=report, approval=request["data"])
    notify_sales = tool_call(agent="human_approval", call=review["call"])
    pending = waiting(approval=request["data"], notified=notify_sales["ok"], notify_error=notify_sales["error"])
    refused = held(error=request["error"], data=request["data"])
    START >> asking >> request >> (
        if_(request["ok"] == False, refused)  # noqa: E712
        .if_(notify == True, review)  # noqa: E712
        .else_(pending)
    )
    review >> notify_sales >> pending
    [pending, refused] >> END

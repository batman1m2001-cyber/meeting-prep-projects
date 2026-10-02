"""How runs start: an email id posted to the service, or the approval link."""
from operonx import END, START, graph
from operonx.app.serve import egress, ingress

from deliver.graph import deliver
from prepare_brief.graph import prepare_brief

from .ops import approve_request, email_request


@graph
def on_email():
    """POST /prepare {"email_id"} → the brief waiting for approval; sales gets the approve/reject links by email."""
    src = ingress()
    asked = email_request(item=src["item"])
    prepare = prepare_brief(email_id=asked["email_id"], notify=True)
    out = egress(item=prepare["outcome"])
    START >> src >> asked >> prepare >> out >> END


@graph
def on_approve(approval, decision):
    """GET /approve?approval=&decision= → Send Brief / Save to KB, or nothing."""
    asked = approve_request(approval=approval, decision=decision)
    send_or_save = deliver(approval_id=asked["approval_id"], decision=asked["decision"])
    out = egress(item=send_or_save["outcome"])
    START >> asked >> send_or_save >> out >> END

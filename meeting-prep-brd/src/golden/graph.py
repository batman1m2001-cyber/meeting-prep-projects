"""The golden emails as an eval: each one through `prepare_brief`, by its
golden mail id — no mail server, nothing sent (the run ends at approval)."""
from operonx import END, START, graph
from operonx.app.serve import egress, ingress

from prepare_brief.graph import prepare_brief

from .ops import case


@graph
def golden_case():
    src = ingress()
    email = case(item=src["item"])
    prepare = prepare_brief(email_id=email["email_id"], notify=email["notify"])
    out = egress(item=prepare["outcome"])
    START >> src >> email >> prepare >> out >> END

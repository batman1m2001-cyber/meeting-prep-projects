"""The golden emails, as an eval: each case is one email through `prepare`,
delivering nothing, judged by the shared scorer (`golden.judge`)."""
from operonx import END, START, graph
from operonx.app.serve import egress, ingress

from golden import ops
from prepare.graph import prepare


@graph
def golden_case():
    src = ingress()
    c = ops.case(item=src["item"])
    p = prepare(mail=c["email"], deliver=False)
    out = egress(item=p["outcome"])
    START >> src >> c >> p >> out >> END


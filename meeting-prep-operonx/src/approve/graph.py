from operonx import END, START, graph
from operonx.app.serve import egress

from approve import ops


@graph
def approve(draft, decision):
    d = ops.decide(draft=draft, decision=decision)
    out = egress(item=d["reply"])
    START >> d >> out >> END

"""How a run starts: a new email (the webhook), or eight o'clock (the sweep)."""
from operonx import END, START, graph
from operonx.app.serve import ingress
from operonx.core.ops import if_

from inbox import ops
from prepare.graph import prepare


@graph
def on_mail():
    src = ingress()
    got = ops.fetch(item=src["item"])
    skip = ops.ignore()
    brief = prepare(email=got["email"], deliver=True)
    START >> src >> got >> if_(got["ours"] == True, skip).else_(brief)  # noqa: E712
    [skip, brief] >> END


@graph
def sweep():
    src = ingress()  # the tick
    ids = ops.unread()
    one = ops.each(ids=ids["ids"])
    got = ops.fetch(item=one["item"])
    brief = prepare(email=got["email"], deliver=True)
    START >> src >> ids >> one >> got >> brief >> END

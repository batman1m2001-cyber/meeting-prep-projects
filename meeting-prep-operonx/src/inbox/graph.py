"""How a run starts: a new email (the webhook), or eight o'clock (the sweep).

    inbox      Email Inbox → New Customer Email: read the new message whole; our own
               mail (the approval requests) is ignored, anything else goes to prepare
"""
from operonx import END, PARENT, START, graph
from operonx.app.serve import ingress
from operonx.core.ops import if_

from inbox import ops
from prepare.graph import prepare


@graph
def inbox(item):
    """Email Inbox → New Customer Email."""
    fetch = ops.fetch(item=item)
    ignore = ops.ignore()
    fetch["email"] >> PARENT["email"]
    fetch["ours"] >> PARENT["ours"]
    START >> fetch >> if_(fetch["ours"] == True, ignore).else_(END)  # noqa: E712
    ignore >> END


@graph
def on_mail():
    src = ingress()
    new = inbox(item=src["item"], name="inbox")
    brief = prepare(email=new["email"], deliver=True, name="prepare")
    START >> src >> new >> if_(new["ours"] == True, END).else_(brief)  # noqa: E712
    brief >> END


@graph
def sweep():
    src = ingress()  # the tick
    ids = ops.unread()
    one = ops.each(ids=ids["ids"])
    got = ops.fetch(item=one["item"])
    brief = prepare(email=got["email"], deliver=True, name="prepare")
    START >> src >> ids >> one >> got >> brief >> END

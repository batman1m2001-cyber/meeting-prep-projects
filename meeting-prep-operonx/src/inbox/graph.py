"""How a run starts: a new email (the webhook), or eight o'clock (the sweep).

    inbox      Email Inbox → New Customer Email: read the new message whole; our own
               mail (the approval requests) is ignored, anything else goes to prepare
"""
from operonx import END, PARENT, START, graph
from operonx.core.ops import if_

from inbox import ops
from prepare import graph as prepare_graph


@graph
def new_customer_email(item):
    """Email Inbox → New Customer Email."""
    fetch = ops.fetch(item=item)
    ignore = ops.ignore()
    fetch["email"] >> PARENT["email"]
    fetch["ours"] >> PARENT["ours"]
    START >> fetch >> if_(fetch["ours"] == True, ignore).else_(END)  # noqa: E712
    ignore >> END


@graph
def on_mail(item):
    """Mailpit's new-mail hook: its whole JSON body is `item` (`Service(input="item")`)."""
    inbox = new_customer_email(item=item)
    prepare = prepare_graph.prepare(mail=inbox["email"], deliver=True)
    START >> inbox >> if_(inbox["ours"] == True, END).else_(prepare)  # noqa: E712
    prepare >> END


@graph
def sweep():
    """Eight o'clock: every unread email through prepare."""
    ids = ops.unread()
    one = ops.each(ids=ids["ids"])
    got = ops.fetch(item=one["item"])
    prepare = prepare_graph.prepare(mail=got["email"], deliver=True)
    START >> ids >> one >> got >> prepare >> END

"""approve(draft, decision): the link in the approval email.

    send_or_save   Send Brief / Save to KB — the brief's last box:
        decide ─► send (to sales) ─► save (into the knowledge base) ─► reply
"""
from operonx import END, START, graph
from operonx.app.serve import egress

from approve import ops


@graph
def send_brief_or_save(draft, decision):
    """Approve → the brief goes to sales and into memory. Reject → nothing."""
    decide = ops.decide(draft=draft, decision=decision)
    send = ops.send(draft=decide["decided"])
    save = ops.save(draft=decide["decided"])
    reply = ops.reply(asked=draft, draft=decide["decided"])
    START >> decide >> send >> save >> reply >> END


@graph
def approve(draft, decision):
    send_or_save = send_brief_or_save(draft=draft, decision=decision)
    out = egress(item=send_or_save["reply"])
    START >> send_or_save >> out >> END

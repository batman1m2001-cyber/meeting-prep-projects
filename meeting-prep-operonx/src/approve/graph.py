"""approve(draft, decision): the link in the approval email. Served as is: the link's
query (?draft=&decision=) fills the parameters, and the reply is {"reply": ...}.

    send_or_save   Send Brief / Save to KB — the brief's last box:
        decide ─► send (to sales) ─► save (into the knowledge base) ─► reply
"""
from operonx import END, START, graph

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
    """Sales clicked the approval link: record the decision, and when it is approve, send the brief to sales and keep it as memory for the next run."""
    send_or_save = send_brief_or_save(draft=draft, decision=decision)
    START >> send_or_save >> END

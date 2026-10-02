"""The meeting-prep assistant: read this file first.

    services (one server, :8200)
      mail     webhook  POST /mail       Mailpit's new-mail hook → prepare a brief, ask for approval
      approve  http     GET  /approve    the link in the approval email → send the brief, remember it
      morning  schedule 08:00            catch up on anything unread
    evals
      golden   the 19 golden emails through prepare, nothing delivered; fails under 90%

    operonx-serve             # the three services
    operonx-run golden        # the eval
"""
from operonx.app import Application, Eval, Service, http, schedule, webhook

from approve.graph import approve
from golden.graph import golden_case, judged
from inbox.graph import on_mail, sweep

PORT = 8200

APP = Application(
    "meeting-prep",
    services=[
        Service("mail", webhook("/mail", port=PORT), graph=on_mail, max_inflight=20),
        Service("approve", http("GET", "/approve", port=PORT), graph=approve),
        Service("morning", schedule(at="08:00", port=PORT), graph=sweep),
    ],
    jobs=[Eval("golden", graph=golden_case, dataset="datasets/golden.jsonl", evaluators=[judged], threshold=0.9)],
    trace=["trace_local:default"],
)

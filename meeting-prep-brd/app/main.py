"""The meeting-prep assistant as the course brief designs it: read this file first.

    services (one server, :8400)
      prepare  http POST /prepare {"email_id"}   a new customer email → seven agents → a brief waiting for approval
      approve  http GET  /approve?approval=&decision=approve|reject
                                                 the Human Approval link → Send Brief / Save to KB
    evals
      golden   the 19 golden emails through prepare_brief, nothing sent; fails under 90%

    operonx-serve            # the two services
    operonx-run golden       # the eval

Mailpit's new-mail webhook stays with the optimized build (:8200); this build
is started by its own endpoint.
"""
from operonx.app import Application, Eval, Service, http

from doors.graph import on_approve, on_email
from golden._judge import judged
from golden.graph import golden_case

PORT = 8400

APP = Application(
    "meeting-prep-brd",
    services=[
        Service("prepare", http("POST", "/prepare", port=PORT), graph=on_email),
        Service("approve", http("GET", "/approve", port=PORT), graph=on_approve),
    ],
    jobs=[Eval("golden", graph=golden_case, dataset="datasets/golden.jsonl", evaluators=[judged], threshold=0.9)],
    trace=["trace_local:default"],
)

"""The golden emails, as an eval: each case is one email through `prepare`,
delivering nothing, judged by the shared scorer (`golden.judge`)."""
from operonx import END, START, graph

from prepare.graph import prepare


@graph
def golden_case(email):
    """One golden email (the case's input, as `Eval(input="email")` hands it over)."""
    p = prepare(mail=email, deliver=False)
    START >> p >> END

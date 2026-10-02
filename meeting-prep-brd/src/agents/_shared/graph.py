"""The tool harness as graphs: one call through its six steps, and a turn's
calls fanned out."""
from operonx import END, START, graph

from .ops import as_data, audit, authenticate, authorize, each_call, execute, rate_limit, validate


@graph
def tool_call(agent, call):
    """One tool call: validate → authenticate → authorize → rate_limit → audit → execute,
    then the result as the tool message (`message`) and any screen `alert`."""
    checked = validate(call=call)
    who = authenticate(agent=agent, error=checked["error"])
    allowed = authorize(identity=who["identity"], tool=checked["tool"], args=checked["args"], error=who["error"])
    limited = rate_limit(identity=who["identity"], tool=checked["tool"], error=allowed["error"])
    logged = audit(identity=who["identity"], tool=checked["tool"], args=checked["args"], error=limited["error"])
    ran = execute(tool=checked["tool"], args=checked["args"], error=limited["error"])
    data = as_data(call_id=checked["call_id"], tool=checked["tool"], ok=ran["ok"], result=ran["result"],
                   error=ran["error"])
    START >> checked >> who >> allowed >> limited >> logged >> ran >> data >> END


@graph
def run_tools(agent, tool_calls):
    """Every tool call of one model turn, at once, each through the harness."""
    calls = each_call(tool_calls=tool_calls)
    call = tool_call(agent=agent, call=calls["call"].parallel(max=8))
    START >> calls >> call >> END

"""Email Agent: an LLM with the mail tools (and the CRM, to tell a new
customer), in a loop — model → tool calls through the harness → model —
until it answers.

    email_agent        task "analyse": a new email → its facts, and brief / skip / block
    email_agent_send   task "send": an approved brief → sent to sales, its status
"""
import operator

from operonx import END, PARENT, START, graph
from operonx.core.ops import if_
from operonx.providers.ops import LLMOp
from operonx.reducers import add_messages

from .._shared.graph import run_tools
from .._shared.ops import count_turn, reply, tool_results, tool_schemas
from .ops import email_facts, opening, send_opening, sent


@graph
def email_agent(email_id):
    """Reads the new email, extracts sender, company and content, says if it is a customer's."""
    PARENT.declare(messages=[], alerts=[], tools=[], turns=0,
                   reducers={"messages": add_messages, "alerts": operator.add})
    task = opening(email_id=email_id)
    schemas = tool_schemas(agent="email_agent")
    task["messages"] >> PARENT["messages"]
    schemas["tools"] >> PARENT["tools"]
    turn = count_turn(turns=PARENT["turns"], max_turns=6)
    turn["turns"] >> PARENT["turns"]
    model = LLMOp.of(resource="agent", messages=PARENT["messages"], tools=PARENT["tools"],
                     tool_choice=turn["tool_choice"])
    said = reply(content=model["content"], tool_calls=model["tool_calls"], finish_reason=model["finish_reason"])
    said["messages"] >> PARENT["messages"]
    tools = run_tools(agent="email_agent", tool_calls=said["tool_calls"])
    results = tool_results(messages=tools["message"].collect(), alerts=tools["alert"].collect())
    results["messages"] >> PARENT["messages"]
    results["alerts"] >> PARENT["alerts"]
    facts = email_facts(email_id=email_id, content=said["content"], messages=PARENT["messages"],
                        alerts=PARENT["alerts"])
    START >> [task, schemas] >> turn >> model >> said >> if_(said["done"] == True, facts).else_(tools)  # noqa: E712
    tools >> results >> turn
    facts >> END


@graph
def email_agent_send(approval_id, to, subject, body):
    """Sends an approved brief to the named recipient and tracks its status."""
    PARENT.declare(messages=[], alerts=[], tools=[], turns=0,
                   reducers={"messages": add_messages, "alerts": operator.add})
    task = send_opening(approval_id=approval_id, to=to, subject=subject, body=body)
    schemas = tool_schemas(agent="email_agent")
    task["messages"] >> PARENT["messages"]
    schemas["tools"] >> PARENT["tools"]
    turn = count_turn(turns=PARENT["turns"], max_turns=4)
    turn["turns"] >> PARENT["turns"]
    model = LLMOp.of(resource="agent", messages=PARENT["messages"], tools=PARENT["tools"],
                     tool_choice=turn["tool_choice"])
    said = reply(content=model["content"], tool_calls=model["tool_calls"], finish_reason=model["finish_reason"])
    said["messages"] >> PARENT["messages"]
    tools = run_tools(agent="email_agent", tool_calls=said["tool_calls"])
    results = tool_results(messages=tools["message"].collect(), alerts=tools["alert"].collect())
    results["messages"] >> PARENT["messages"]
    results["alerts"] >> PARENT["alerts"]
    done = sent(content=said["content"], messages=PARENT["messages"], alerts=PARENT["alerts"])
    START >> [task, schemas] >> turn >> model >> said >> if_(said["done"] == True, done).else_(tools)  # noqa: E712
    tools >> results >> turn
    done >> END

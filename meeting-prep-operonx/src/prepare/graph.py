"""prepare(email): from one email to a brief waiting for approval.

    screen ─ attack ─► blocked
      └► triage (LLM) ─ not a lead ─► not_a_lead
           └► identify (CRM over MCP)
                ├► crm (MCP) ─┐
                ├► calendar ──┤
                ├► recall ────┼► evidence ► brief (LLM) ► check ─ ok ─► request_approval
                └► research ──┘                              └ leak ─► held
                   website · news · people: three agents in parallel,
                   each starting from company memory; identical tool
                   calls across them hit the network once per run
"""
from operonx import END, PARENT, START, graph
from operonx.agents import build_react_agent, get_tool_definitions
from operonx.agents.ops.model_ops import adapt_llm_output, turn_tool_choice
from operonx.agents.policy import ToolPolicy
from operonx.core.utils.auto_name import register_skip
from operonx.core.ops import if_
from operonx.providers.ops import LLMOp

from prepare import ops, tools
from prepare._prompts import BRIEF, RESEARCH, TRIAGE
from prepare.memory import CompanyMemory, place_memory

RESEARCH_DEFS = get_tool_definitions(tools.RESEARCH_TOOLS)

# Unattended: the agents may read (both tools are read-only); anything else is refused, never asked.
READ_ONLY = ToolPolicy(default="deny", readonly="allow", destructive="deny")


def call_model(messages=None, last_turn=False):
    """`make_llm_caller("assistant", tools=…)`, with the company memory seated first."""

    @graph
    def model(messages=None, last_turn=False):
        seated = place_memory(messages=messages)
        choice = turn_tool_choice(last_turn=last_turn)
        llm = LLMOp.of(resource="assistant", messages=seated["messages"], tools=RESEARCH_DEFS,
                       tool_choice=choice["tool_choice"])
        adapted = adapt_llm_output(content=llm["content"], tool_calls=llm["tool_calls"],
                                   finish_reason=llm["finish_reason"])
        for key in ("assistant_message", "tool_calls", "done", "finish_reason", "truncated"):
            adapted[key] >> PARENT[key]
        START >> seated >> choice >> llm >> adapted >> END

    return model(messages=messages, last_turn=last_turn)


call_model.tools = RESEARCH_DEFS  # counted against the agent's token budget
register_skip(call_model)


def researcher():
    return build_react_agent(
        call_model=call_model,
        system=RESEARCH,
        max_turns=4,
        memory_providers=[CompanyMemory()],
        policy=READ_ONLY,
    )


@graph
def prepare(email, deliver):
    gate = ops.screen(email=email)
    stop = ops.blocked(reason=gate["reason"])
    read = ops.letter(email=email)
    triage = LLMOp.of(
        resource="assistant",
        prompt={"system": TRIAGE, "user": "{letter}"},
        fields=["is_lead: bool", "intent: str", "contact: str"],
        parser="json",
        on_failure="error",
        letter=read["text"],
    )
    skip = ops.not_a_lead(intent=triage["intent"])

    who = ops.identify(email=email)
    crm = ops.crm(company_id=who["company_id"])
    cal = ops.calendar(company_id=who["company_id"])
    memory = ops.recall(company=who["company"])
    asks = ops.research_tasks(company=who["company"])
    website = researcher()(messages=asks["website"])
    news = researcher()(messages=asks["news"])
    people = researcher()(messages=asks["people"])

    facts = ops.evidence(
        email=email, company=who["company"], contacts=crm["contacts"], history=crm["history"],
        meetings=cal["meetings"], memory=memory["memory"],
        website=website["final"], news=news["final"], people=people["final"],
    )
    brief = LLMOp.of(
        resource="assistant",
        prompt={"system": BRIEF, "user": "Company: {company}\n\nEvidence:\n{evidence}"},
        company=who["name"],
        evidence=facts["text"],
    )
    check = ops.check_brief(brief=brief["content"], company=who["company"])
    ask = ops.request_approval(email=email, company=who["company"], brief=brief["content"], deliver=deliver)
    hold = ops.held(company=who["company"], brief=brief["content"], problems=check["problems"])
    done = ops.settle(a=stop["outcome"], b=skip["outcome"], c=ask["outcome"], d=hold["outcome"])

    START >> gate >> if_(gate["blocked"] == True, stop).else_(read)  # noqa: E712
    read >> triage >> if_(triage["is_lead"] == False, skip).else_(who)  # noqa: E712
    who >> [crm, cal, memory, asks]
    asks >> [website, news, people]
    [crm, cal, memory, website, news, people] >> facts
    facts >> brief >> check >> if_(check["ok"] == True, ask).else_(hold)  # noqa: E712
    [stop, skip, ask, hold] >> done >> END

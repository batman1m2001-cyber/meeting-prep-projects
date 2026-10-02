"""prepare(email): from one email to a brief waiting for approval.

Drawn as the course brief draws it: one zone (a nested `@graph`) per box.

    email ─ attack ─► blocked                       Email Agent
      └ not a lead ─► skip
      └► extract_company (CRM over MCP)              Extract Company Name
          ├► web_research ─┐  website · news · people: three ReAct agents in
          ├► calendar ─────┤  parallel, each starting from company memory;
          └► company_info ─┘  identical tool calls hit the network once per run
                └► memory (merge · dedupe) ► report (LLM · check)
                     └► human_approval ─ ok ─► request_approval   (the run ends;
                                       └ leak ─► held              the link goes on
                                                                   in approve: send_or_save)
Every zone hands plain values on; none collects a stream.
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
from prepare.memory import CompanyMemory, company_memory, place_memory

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


# ── the zones, one per box of the brief ───────────────────────────────────
@graph
def email_agent(email):
    """Email Agent: the security gate, then an LLM reads the letter and says if it is a lead."""
    gate = ops.screen(email=email)
    blocked = ops.blocked(reason=gate["reason"])
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
    verdict = ops.screened(blocked=blocked["outcome"], skipped=skip["outcome"])
    START >> gate >> if_(gate["blocked"] == True, blocked).else_(read)  # noqa: E712
    read >> triage >> if_(triage["is_lead"] == False, skip).else_(verdict)  # noqa: E712
    [blocked, skip] >> verdict >> END


@graph
def extract_company(email):
    """Extract Company Name: the sender's domain, looked up in the CRM (over MCP)."""
    identify = ops.identify(email=email)
    START >> identify >> END


@graph
def web_research(company=None):
    """Web Research Agent: three ReAct agents (website, news, people) at once."""
    tasks = ops.research_tasks(company=company)
    known = company_memory(website=tasks["website"], news=tasks["news"], people=tasks["people"],
                           name="company_memory")
    website = researcher()(messages=tasks["website"])
    news = researcher()(messages=tasks["news"])
    people = researcher()(messages=tasks["people"])
    website["final"] >> PARENT["website"]
    news["final"] >> PARENT["news"]
    people["final"] >> PARENT["people"]
    START >> tasks >> known >> [website, news, people]
    [website, news, people] >> END


@graph
def calendar_agent(company_id=None):
    """Calendar Agent: meetings already booked with the company (over MCP)."""
    meetings = ops.calendar(company_id=company_id)
    START >> meetings >> END


@graph
def company_info(company=None, company_id=None):
    """Company Info Agent: CRM contacts and history (over MCP) and the knowledge base."""
    crm = ops.crm(company_id=company_id)
    kb = ops.recall(company=company)
    START >> [crm, kb]
    [crm, kb] >> END


@graph
def memory_agent(email, company=None, contacts=None, history=None, meetings=None, notes=None,
                 website=None, news=None, people=None):
    """Memory Agent: every source merged into one evidence pack, each fact once."""
    merge = ops.evidence(
        email=email, company=company, contacts=contacts, history=history, meetings=meetings,
        memory=notes, website=website, news=news, people=people,
    )
    dedupe = ops.dedupe(lines=merge["lines"])
    START >> merge >> dedupe >> END


@graph
def report_agent(company=None, company_name=None, evidence=None):
    """Report Agent: an LLM writes the brief from the evidence; code checks it for leaks."""
    brief = LLMOp.of(
        resource="assistant",
        prompt={"system": BRIEF, "user": "Company: {company}\n\nEvidence:\n{evidence}"},
        company=company_name,
        evidence=evidence,
    )
    check = ops.check_brief(brief=brief["content"], company=company)
    brief["content"] >> PARENT["brief"]
    START >> brief >> check >> END


@graph
def human_approval(email, deliver, company=None, brief=None, ok=None, problems=None):
    """Human Approval: a clean brief waits for sales' click; a leaky one is held."""
    ask = ops.request_approval(email=email, company=company, brief=brief, deliver=deliver)
    hold = ops.held(company=company, brief=brief, problems=problems)
    waiting = ops.settle(a=ask["outcome"], b=hold["outcome"])
    START >> if_(ok == True, ask).else_(hold)  # noqa: E712
    [ask, hold] >> waiting >> END


# ── prepare: the brief's diagram, top to bottom ───────────────────────────
@graph
def prepare(email, deliver):
    screened = email_agent(email=email, name="email")
    who = extract_company(email=email, name="extract_company")
    web = web_research(company=who["company"], name="web_research")
    cal = calendar_agent(company_id=who["company_id"], name="calendar")
    info = company_info(company=who["company"], company_id=who["company_id"], name="company_info")
    pack = memory_agent(
        email=email, company=who["company"], contacts=info["contacts"], history=info["history"],
        meetings=cal["meetings"], notes=info["memory"],
        website=web["website"], news=web["news"], people=web["people"], name="memory",
    )
    brief = report_agent(company=who["company"], company_name=who["name"], evidence=pack["text"], name="report")
    approval = human_approval(email=email, deliver=deliver, company=who["company"], brief=brief["brief"],
                              ok=brief["ok"], problems=brief["problems"], name="human_approval")
    done = ops.settle(a=screened["outcome"], b=approval["outcome"])

    START >> screened >> if_(screened["lead"] == True, who).else_(done)  # noqa: E712
    who >> [web, cal, info]
    [web, cal, info] >> pack >> brief >> approval >> done >> END

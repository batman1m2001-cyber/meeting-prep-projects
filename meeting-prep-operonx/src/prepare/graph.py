"""prepare(mail): from one email to a brief waiting for approval.

Drawn as the course brief draws it: one zone (a nested `@graph`) per box.

    email ─ attack ─► blocked                       Email Agent
      └ not a lead ─► skip
      └► extract_company (CRM over MCP)              Extract Company Name
          ├► web_research ─┐  website · news · people: one research agent run three
          ├► calendar ─────┤  times in parallel, each starting from company memory;
          └► company_info ─┘  identical tool calls hit the network once per run
                └► memory (merge · dedupe) ► report (LLM · check)
                     └► human_approval ─ ok ─► request_approval   (the run ends;
                                       └ leak ─► held              the link goes on
                                                                   in approve: send_or_save)
Every zone hands plain values on; none collects a stream.
"""
from operonx import END, PARENT, START, graph
from operonx.agents import Agent, AgentOp, Model, ToolPolicy, UsageLimits
from operonx.core.ops import if_
from operonx.providers.ops import LLMOp

from prepare import memory, ops, tools
from prepare._prompts import BRIEF, TRIAGE

# Unattended: the agents may read (both tools are read-only); anything else is refused, never asked.
READ_ONLY = ToolPolicy(default="deny", readonly="allow", destructive="deny")

# ── the research agent ────────────────────────────────────────────────────
# One agent, defined once; `web_research_agent` runs it three times. Its company memory
# comes in as `deps` and sits in its system prompt (`memory.instructions`); its fourth
# model call is told to answer and cannot call tools.
researcher = Agent(
    name="researcher",
    model=Model("assistant"),
    instructions=memory.instructions,
    tools=tools.RESEARCH_TOOLS,
    limits=UsageLimits(turns=4),
    policy=READ_ONLY,
)


# ── the zones, one per box of the brief ───────────────────────────────────
# A zone's node is named by the variable `prepare` assigns it to (`email`, `extract_company`,
# …), so a zone's @graph is named after its box instead (`email_agent`, …).
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
    verdict = ops.screened(blocked=blocked["outcome"], skipped=skip["outcome"], error=triage["error"])
    START >> gate >> if_(gate["blocked"] == True, blocked).else_(read)  # noqa: E712
    read >> triage >> if_(triage["is_lead"] == False, skip).else_(verdict)  # noqa: E712
    [blocked, skip] >> verdict >> END


@graph
def extract_company_name(email):
    """Extract Company Name: the sender's domain, looked up in the CRM (over MCP)."""
    identify = ops.identify(email=email)
    START >> identify >> END


@graph
def web_research_agent(company=None):
    """Web Research Agent: the research agent on three tasks (website, news, people) at once."""
    tasks = ops.research_tasks(company=company)
    company_memory = ops.company_memory(website=tasks["website"], news=tasks["news"], people=tasks["people"])
    website = AgentOp.of(agent=researcher, input=tasks["website"], deps=company_memory["website"])
    news = AgentOp.of(agent=researcher, input=tasks["news"], deps=company_memory["news"])
    people = AgentOp.of(agent=researcher, input=tasks["people"], deps=company_memory["people"])
    website["output"] >> PARENT["website"]
    news["output"] >> PARENT["news"]
    people["output"] >> PARENT["people"]
    START >> tasks >> company_memory >> [website, news, people] >> END


@graph
def calendar_agent(company_id=None):
    """Calendar Agent: meetings already booked with the company (over MCP)."""
    meetings = ops.calendar(company_id=company_id)
    START >> meetings >> END


@graph
def company_info_agent(company=None, company_id=None):
    """Company Info Agent: CRM contacts and history (over MCP) and the knowledge base."""
    crm = ops.crm(company_id=company_id)
    kb = ops.recall(company=company)
    START >> [crm, kb] >> END


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
def human_approval_gate(email, deliver, company=None, brief=None, ok=None, problems=None):
    """Human Approval: a clean brief waits for sales' click; a leaky one is held."""
    ask = ops.request_approval(email=email, company=company, brief=brief, deliver=deliver)
    hold = ops.held(company=company, brief=brief, problems=problems)
    waiting = ops.settle(a=ask["outcome"], b=hold["outcome"])
    START >> if_(ok == True, ask).else_(hold)  # noqa: E712
    [ask, hold] >> waiting >> END


# ── prepare: the brief's diagram, top to bottom ───────────────────────────
@graph
def prepare(mail, deliver):
    email = email_agent(email=mail)
    extract_company = extract_company_name(email=mail)
    web_research = web_research_agent(company=extract_company["company"])
    calendar = calendar_agent(company_id=extract_company["company_id"])
    company_info = company_info_agent(company=extract_company["company"], company_id=extract_company["company_id"])
    memory = memory_agent(
        email=mail, company=extract_company["company"], contacts=company_info["contacts"],
        history=company_info["history"], meetings=calendar["meetings"], notes=company_info["memory"],
        website=web_research["website"], news=web_research["news"], people=web_research["people"],
    )
    report = report_agent(company=extract_company["company"], company_name=extract_company["name"],
                          evidence=memory["text"])
    human_approval = human_approval_gate(email=mail, deliver=deliver, company=extract_company["company"],
                                         brief=report["brief"], ok=report["ok"], problems=report["problems"])
    done = ops.settle(a=email["outcome"], b=human_approval["outcome"])

    START >> email >> if_(email["lead"] == True, extract_company).else_(done)  # noqa: E712
    extract_company >> [web_research, calendar, company_info] >> memory >> report >> human_approval >> done >> END

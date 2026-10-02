"""prepare_brief(email_id, notify): the course brief's flow diagram, one node per box.

    Email Agent ─ brief ─► Extract Company Name ─► Web Research Agent ─┐
               └ skip / block ─► no_brief         ─► Calendar Agent ────┼─► Memory Agent ─► Report Agent ─► Human Approval
                                                  ─► Company Info Agent ┘                                     (a person: the run
                                                                                                                 ends; `deliver` goes on)
Six agents (an LLM with its own MCP tools, in a loop), one plain step
(Extract Company Name) and one person (Human Approval). `notify` emails
sales the approve/reject links; the eval runs with it off, so it sends nothing.
"""
from operonx import END, START, graph
from operonx.core.ops import if_

from agents.calendar_agent.graph import calendar_agent
from agents.company_info_agent.graph import company_info_agent
from agents.email_agent.graph import email_agent
from agents.memory_agent.graph import memory_agent
from agents.report_agent.graph import report_agent
from agents.web_research_agent.graph import web_research_agent
from extract_company.graph import extract_company
from human_approval.graph import human_approval

from .ops import prepared, stopped


@graph
def prepare_brief(email_id, notify):
    """A new email → a brief waiting for approval, or why there is none."""
    email = email_agent(email_id=email_id)
    extract_company_name = extract_company(facts=email["facts"])
    company = extract_company_name["company"]
    web_research = web_research_agent(company=company)
    calendar = calendar_agent(company=company)
    company_info = company_info_agent(company=company)
    memory = memory_agent(company=company, facts=email["facts"], research=web_research["research"],
                          meetings=calendar["meetings"], info=company_info["info"])
    report = report_agent(company=company, facts=email["facts"], context=memory["context"],
                          profile=memory["profile"])
    review = human_approval(report=report["report"], notify=notify)
    no_brief = stopped(email_id=email_id, action=email["action"], reason=email["reason"],
                       screened=email["screened"])
    brief = prepared(
        email_id=email_id, company=company, report=report["report"], approval=review["approval"],
        email_screened=email["screened"], research_screened=web_research["screened"],
        calendar_screened=calendar["screened"], info_screened=company_info["screened"],
        memory_screened=memory["screened"], report_screened=report["screened"],
    )
    START >> email >> if_(email["action"] == "brief", extract_company_name).else_(no_brief)
    extract_company_name >> [web_research, calendar, company_info] >> memory >> report >> review >> brief
    [no_brief, brief] >> END

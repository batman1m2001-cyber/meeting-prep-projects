"""The brief's six agents, one package each, and what they share.

Each agent is an LLM that reaches the world only through its own MCP tools,
in a loop: model → tool calls (each through the 6-step tool harness) →
model … until it answers with its structured output.

    email_agent           Email Agent
    web_research_agent    Web Research Agent
    calendar_agent        Calendar Agent
    company_info_agent    Company Info Agent
    memory_agent          Memory Agent
    report_agent          Report Generation Agent
    _shared               the tool harness and the loop's steps

Extract Company Name (`extract_company/`) is a plain step, and Human Approval
(`human_approval/`) is a person: neither is an agent.
"""

from agents._shared.graph import run_tools, tool_call
from agents._shared.ops import parsed
from agents.calendar_agent.graph import calendar_agent
from agents.company_info_agent.graph import company_info_agent
from agents.email_agent.graph import email_agent, email_agent_send
from agents.memory_agent.graph import memory_agent
from agents.report_agent.graph import report_agent
from agents.web_research_agent.graph import web_research_agent

__all__ = [
    "calendar_agent", "company_info_agent", "email_agent", "email_agent_send",
    "memory_agent", "parsed", "report_agent", "run_tools", "tool_call", "web_research_agent",
]

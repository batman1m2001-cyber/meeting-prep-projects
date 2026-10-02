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

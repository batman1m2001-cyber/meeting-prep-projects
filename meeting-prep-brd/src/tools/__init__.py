"""The agents' tools: one MCP server (stdio) per tool group.

    mail      list_new · read · send · status            Email Agent
    crm       find_company · contacts · history          Email Agent, Extract Company Name, Company Info Agent
    calendar  meetings · upcoming                        Calendar Agent
    kb        search · save                              Company Info Agent, Send Brief / Save to KB
    memory    recall · remember · history · user_profile Memory Agent
    report    render_markdown · email_body               Report Generation Agent
    approval  request · status                           Human Approval Agent
    web       search · fetch · news                      Web Research Agent

Each is started as `python -m tools.<name>`. The agents never call these
functions directly: every call goes through the tool harness
(`agents/_shared`), which starts the servers and speaks MCP to them.
"""

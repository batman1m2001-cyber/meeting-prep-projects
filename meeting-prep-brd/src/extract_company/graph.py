"""Extract Company Name — a box in the diagram, not an agent: one LLM
extraction, then a CRM lookup (through the tool harness), no loop."""
from pathlib import Path

from operonx import END, START, graph
from operonx.prompts import prompt
from operonx.providers.ops import LLMOp

from agents import parsed, tool_call

from .ops import company, email_facts, lookup_call

PROJECT = Path(__file__).resolve().parents[2]  # prompts/ is beside src/


@graph
def extract_company(facts):
    """Email facts → {company_name, domain, website, company_id}."""
    view = email_facts(facts=facts)
    extract = LLMOp.of(
        resource="agent",
        prompt=prompt("extract_company", root=PROJECT),
        fields=["company_name: str", "domain: str"],
        parser="json",
        facts=view["text"],
    )
    extract_parsed = parsed(error=extract["error"])
    call = lookup_call(domain=extract["domain"])
    lookup = tool_call(agent="extract_company", call=call["call"])
    found = company(company_name=extract["company_name"], domain=extract["domain"], ok=lookup["ok"],
                    data=lookup["data"], error=lookup["error"])
    START >> view >> extract >> extract_parsed >> call >> lookup >> found >> END

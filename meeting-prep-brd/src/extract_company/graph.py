"""Extract Company Name — a box in the diagram, not an agent: one LLM
extraction, then a CRM lookup (through the tool harness), no loop."""
from operonx import END, START, graph
from operonx.providers.ops import LLMOp

from agents._shared._prompts import PROMPTS
from agents._shared.graph import tool_call
from agents._shared.ops import parsed

from .ops import company, email_facts, lookup_call


@graph
def extract_company(facts):
    """Email facts → {company_name, domain, website, company_id}."""
    view = email_facts(facts=facts)
    extract = LLMOp.of(
        resource="agent",
        prompt={"system": PROMPTS["extract_company"], "user": "{facts}"},
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

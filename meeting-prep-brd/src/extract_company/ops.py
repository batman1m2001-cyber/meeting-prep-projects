"""Extract Company Name: the CRM lookup, and the company every agent after it works on."""
from __future__ import annotations

import json
from typing import Any, Optional

from operonx import op
from prep_world import WEB


@op
def email_facts(facts: dict) -> dict:
    """The facts as the model reads them: quoted data."""
    return {"text": json.dumps(facts, ensure_ascii=False)}


@op
def lookup_call(domain: str) -> dict:
    """The CRM lookup, as a tool call for the harness."""
    return {"call": {"id": "extract-company-lookup", "type": "function",
                     "function": {"name": "crm__find_company", "arguments": json.dumps({"domain_or_name": domain})}}}


@op
def company(company_name: str, domain: str, ok: bool, data: Any = None, error: Optional[str] = None) -> dict:
    """The canonical company: the CRM's record when it has one, else the email's name and domain."""
    if not ok:
        raise ValueError(f"the CRM lookup failed: {error}")
    known = data or {}
    domain = known.get("domain") or domain
    return {"company": {"company_name": known.get("name") or company_name, "domain": domain,
                        "website": f"{WEB}/web/{domain}/", "company_id": known.get("id")}}

"""How a run of `prepare_brief` ends: stopped at the Email Agent, or a brief
waiting for approval. Either way, every screen alert the agents raised."""
from __future__ import annotations

from typing import Optional

from operonx import op


@op
def stopped(email_id: str, action: str, reason: str, screened: Optional[list] = None) -> dict:
    """Not a customer email (skip), or an attack (block): nothing was researched or sent."""
    return {"outcome": {"email_id": email_id, "action": action, "reason": reason, "company": None,
                        "brief": None, "approval": None, "sent": [], "security": screened or []}}


@op
def prepared(email_id: str, company: dict, report: dict, approval: dict,
             email_screened: Optional[list] = None, research_screened: Optional[list] = None,
             calendar_screened: Optional[list] = None, info_screened: Optional[list] = None,
             memory_screened: Optional[list] = None, report_screened: Optional[list] = None) -> dict:
    """The brief, and the approval it waits on (or why it is held)."""
    security = [*(email_screened or []), *(research_screened or []), *(calendar_screened or []),
                *(info_screened or []), *(memory_screened or []), *(report_screened or [])]
    return {"outcome": {"email_id": email_id, "action": "brief", "reason": approval["status"],
                        "company": company["company_id"], "brief": report["markdown"], "approval": approval,
                        "sent": [], "security": security}}

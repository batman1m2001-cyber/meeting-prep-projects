"""Steps 2–4 of the tool harness, as rules: who may call what, with which
arguments, how often. Read from `scopes.yaml`; the special rules are here."""
from __future__ import annotations

import time
from collections import defaultdict, deque
from pathlib import Path

import yaml
from prep_world import world
from prep_world.guard import leaks

from stores import brd

POLICY = yaml.safe_load(Path(__file__).with_name("scopes.yaml").read_text(encoding="utf-8"))
IDENTITIES: dict[str, dict] = POLICY["identities"]
TIMEOUT_S: float = POLICY["timeout_s"]
SALES: str = world()["us"]["sales"]
# Addresses a brief may contain: ours, and the companies' own (their contacts).
ALLOWED_DOMAINS = (world()["us"]["domain"], *(c["domain"] for c in world()["companies"]))

_calls: dict[tuple[str, str], deque] = defaultdict(deque)


def tools_of(identity: str) -> list[str]:
    return list(IDENTITIES[identity]["tools"])


def refusal(identity: str, tool: str, args: dict) -> str | None:
    """Why `identity` may not make this call, or None."""
    if tool not in IDENTITIES[identity]["tools"]:
        return f"{identity} may not call {tool}"
    if tool == "mail__send":
        return _send_refusal(args)
    if tool == "approval__request":
        report = brd.report(int(args["report_id"]))
        if report is None:
            return f"no report {args['report_id']}"
        problems = leaks(report["markdown"], ALLOWED_DOMAINS)
        return f"the report leaks: {'; '.join(problems)}" if problems else None
    return None


def _send_refusal(args: dict) -> str | None:
    """The Email Agent sends only to sales, only an approved brief, and nothing that leaks."""
    if str(args["to"]).strip().lower() != SALES:
        return f"mail may go only to {SALES}, not {args['to']!r}"
    approval = brd.approval(int(args["approval_id"]))
    if approval is None or approval["status"] != "approved":
        return f"approval {args['approval_id']} is not approved"
    problems = leaks(f"{args['subject']}\n{args['body']}", ALLOWED_DOMAINS)
    return f"the email leaks: {'; '.join(problems)}" if problems else None


def over_limit(identity: str, tool: str) -> str | None:
    """Count this call; why it is over the per-minute limit, or None."""
    limit = IDENTITIES[identity].get("per_minute", POLICY["per_minute"])
    now, window = time.monotonic(), _calls[(identity, tool)]
    while window and now - window[0] > 60:
        window.popleft()
    if len(window) >= limit:
        return f"{identity} called {tool} {limit} times in the last minute"
    window.append(now)
    return None

"""The `brd` schema: memory, research runs, the user profile, reports,
approvals, saved briefs and the audit log.

Every function here is one query. The MCP servers in `tools/` call them;
the tool harness calls `approval` (scopes) and `log_call` (audit).
"""
from __future__ import annotations

import json
from typing import Any

import psycopg
from psycopg.rows import dict_row
from prep_world import DB_URL
from prep_world.db import embed, vec


def rows(sql: str, *args: Any) -> list[dict]:
    with psycopg.connect(DB_URL, autocommit=True) as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql, args)
        return [dict(r) for r in cur.fetchall()] if cur.description else []


def _one(sql: str, *args: Any) -> dict | None:
    hit = rows(sql, *args)
    return hit[0] if hit else None


# ── memory ─────────────────────────────────────────────────────────────────
def remember(subject: str, kind: str, content: str, source: str | None) -> dict:
    """Store one item; an item already held (same subject, kind, text) is kept once."""
    hit = _one("INSERT INTO brd.memory_items (subject, kind, content, source, embedding) "
               "VALUES (%s, %s, %s, %s, %s::vector) ON CONFLICT (subject, kind, content) DO NOTHING "
               "RETURNING id", subject, kind, content, source, vec(embed([content])[0]))
    return {"stored": hit is not None, "id": hit["id"] if hit else None}


def recall(subject: str, query: str | None, k: int) -> list[dict]:
    """A subject's items: nearest to `query` when given, else the newest."""
    if query:
        return rows("SELECT kind, content, source, created_at::text, "
                    "round((embedding <=> %s::vector)::numeric, 3)::float AS distance "
                    "FROM brd.memory_items WHERE subject = %s ORDER BY distance LIMIT %s",
                    vec(embed([query])[0]), subject, k)
    return rows("SELECT kind, content, source, created_at::text FROM brd.memory_items "
                "WHERE subject = %s ORDER BY created_at DESC, id DESC LIMIT %s", subject, k)


def add_research_run(company_id: str, email_id: str | None, summary: str, sources: list[str]) -> int:
    return _one("INSERT INTO brd.research_runs (company_id, email_id, summary, sources) "
                "VALUES (%s, %s, %s, %s) RETURNING id", company_id, email_id, summary, json.dumps(sources))["id"]


def research_runs(company_id: str) -> list[dict]:
    return rows("SELECT id, email_id, summary, sources, created_at::text FROM brd.research_runs "
                "WHERE company_id = %s ORDER BY created_at DESC, id DESC", company_id)


def user_profile(user_id: str) -> dict | None:
    return _one("SELECT user_id, name, email, preferences FROM brd.user_profile WHERE user_id = %s", user_id)


# ── reports ────────────────────────────────────────────────────────────────
def save_report(company_id: str | None, title: str, markdown: str) -> int:
    return _one("INSERT INTO brd.reports (company_id, title, markdown) VALUES (%s, %s, %s) RETURNING id",
                company_id, title, markdown)["id"]


def set_email_body(report_id: int, body: str) -> None:
    rows("UPDATE brd.reports SET email_body = %s WHERE id = %s", body, report_id)


def report(report_id: int) -> dict | None:
    return _one("SELECT id, company_id, title, markdown, email_body FROM brd.reports WHERE id = %s", report_id)


# ── approvals ──────────────────────────────────────────────────────────────
def request_approval(task: str, payload: dict) -> int:
    return _one("INSERT INTO brd.approvals (task, payload) VALUES (%s, %s) RETURNING id",
                task, json.dumps(payload))["id"]


def approval(approval_id: int) -> dict | None:
    return _one("SELECT id, task, payload, status, decided_by, decided_at::text FROM brd.approvals WHERE id = %s",
                approval_id)


def decide(approval_id: int, approve: bool, by: str) -> dict | None:
    """Approve or reject a pending request; None when it is not pending (decided twice, or unknown)."""
    return _one("UPDATE brd.approvals SET status = %s, decided_by = %s, decided_at = now() "
                "WHERE id = %s AND status = 'pending' RETURNING id, task, payload, status",
                "approved" if approve else "rejected", by, approval_id)


# ── knowledge base ─────────────────────────────────────────────────────────
def kb_save(company_id: str | None, source: str, content: str) -> int:
    return _one("INSERT INTO brd.kb_chunks (company_id, source, content, embedding) "
                "VALUES (%s, %s, %s, %s::vector) RETURNING id", company_id, source, content,
                vec(embed([content])[0]))["id"]


def kb_search(query: str, company_id: str | None, k: int) -> list[dict]:
    """The nearest chunks in the CRM notes (public, read-only) and the saved briefs (brd)."""
    q = vec(embed([query])[0])
    where = "WHERE company_id = %s" if company_id else ""
    args = (q, company_id) if company_id else (q,)
    union = (f"SELECT company_id, source, content, embedding <=> %s::vector AS d FROM public.kb_chunks {where} "
             f"UNION ALL SELECT company_id, source, content, embedding <=> %s::vector AS d FROM brd.kb_chunks {where}")
    return rows(f"SELECT company_id, source, content, round(d::numeric, 3)::float AS distance "
                f"FROM ({union}) chunks ORDER BY d LIMIT %s", *args, *args, k)


# ── audit ──────────────────────────────────────────────────────────────────
def log_call(agent: str, tool: str, args: dict, verdict: str) -> int:
    return _one("INSERT INTO brd.audit (agent, tool, args, verdict) VALUES (%s, %s, %s, %s) RETURNING id",
                agent, tool, json.dumps(args, default=str), verdict)["id"]

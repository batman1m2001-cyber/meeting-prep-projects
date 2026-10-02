"""Postgres + pgvector: the CRM, the calendar and the knowledge base.

    uv run prep-seed        drop, create and fill every table from world.yaml

Tables
    companies     id, name, domain, industry, hq, size, about
    contacts      company_id, name, title, email
    interactions  company_id, date, kind, note             the CRM history
    meetings      company_id, starts_at, title, attendees  the calendar
    kb_chunks     company_id, source, content, embedding   memory: notes and past briefs

The knowledge base starts with the CRM notes; every approved brief is added to it.
Embeddings come from OPENAI_BASE_URL: re-seed after switching between the mock
model and a real one, since their vectors don't mix.
"""
from __future__ import annotations

import json
import sys
from contextlib import contextmanager

import psycopg
from openai import OpenAI

from prep_world import DB_URL, EMBED_DIM, EMBED_MODEL, MODEL_KEY, MODEL_URL, world

SCHEMA = f"""
CREATE EXTENSION IF NOT EXISTS vector;
DROP TABLE IF EXISTS drafts, kb_chunks, meetings, interactions, contacts, companies;
CREATE TABLE companies (
    id text PRIMARY KEY, name text NOT NULL, domain text UNIQUE NOT NULL,
    industry text, hq text, size text, about text);
CREATE TABLE contacts (
    id serial PRIMARY KEY, company_id text REFERENCES companies, name text, title text, email text UNIQUE);
CREATE TABLE interactions (
    id serial PRIMARY KEY, company_id text REFERENCES companies, date date, kind text, note text);
CREATE TABLE meetings (
    id serial PRIMARY KEY, company_id text REFERENCES companies, starts_at timestamp, title text,
    attendees text[]);
CREATE TABLE kb_chunks (
    id serial PRIMARY KEY, company_id text REFERENCES companies, source text, content text,
    embedding vector({EMBED_DIM}), created_at timestamp DEFAULT now());
CREATE TABLE drafts (
    id serial PRIMARY KEY, email_id text, company_id text REFERENCES companies, subject text,
    brief text, status text DEFAULT 'pending', created_at timestamp DEFAULT now(), decided_at timestamp);
"""


@contextmanager
def connect():
    with psycopg.connect(DB_URL, autocommit=True) as conn:
        yield conn


def rows(sql: str, *args) -> list[dict]:
    with connect() as conn, conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        cur.execute(sql, args)
        return [dict(r) for r in cur.fetchall()]


def embed(texts: list[str]) -> list[list[float]]:
    r = OpenAI(base_url=MODEL_URL, api_key=MODEL_KEY).embeddings.create(model=EMBED_MODEL, input=texts)
    return [d.embedding for d in r.data]


def vec(v: list[float]) -> str:
    return "[" + ",".join(f"{x:.6f}" for x in v) + "]"


# ── the queries the tools and the builds use ──────────────────────────────
def find_company(domain_or_name: str) -> dict | None:
    k = domain_or_name.lower().strip()
    hit = rows("SELECT * FROM companies WHERE lower(domain) = %s OR lower(name) = %s OR id = %s", k, k, k)
    return hit[0] if hit else None


def contacts(company_id: str) -> list[dict]:
    return rows("SELECT name, title, email FROM contacts WHERE company_id = %s ORDER BY id", company_id)


def history(company_id: str) -> list[dict]:
    return rows("SELECT date::text, kind, note FROM interactions WHERE company_id = %s ORDER BY date", company_id)


def meetings(company_id: str) -> list[dict]:
    return rows("SELECT starts_at::text, title, attendees FROM meetings WHERE company_id = %s ORDER BY starts_at",
                company_id)


def recall(query: str, k: int = 3, company_id: str | None = None) -> list[dict]:
    """The knowledge-base chunks nearest to `query` (cosine distance)."""
    q = vec(embed([query])[0])
    where = "WHERE company_id = %s" if company_id else ""
    args = (q, company_id, k) if company_id else (q, k)
    return rows(f"SELECT company_id, source, content, round((embedding <=> %s::vector)::numeric, 3)::float AS distance "
                f"FROM kb_chunks {where} ORDER BY distance LIMIT %s", *args)


def remember(company_id: str, source: str, content: str) -> None:
    """Add a chunk to the knowledge base — e.g. an approved brief."""
    with connect() as conn:
        conn.execute("INSERT INTO kb_chunks (company_id, source, content, embedding) VALUES (%s, %s, %s, %s::vector)",
                     (company_id, source, content, vec(embed([content])[0])))


# ── drafts: approval in two steps, durable across restarts ────────────────
def save_draft(email_id: str, company_id: str, subject: str, brief: str) -> int:
    with connect() as conn:
        return conn.execute("INSERT INTO drafts (email_id, company_id, subject, brief) VALUES (%s, %s, %s, %s) "
                            "RETURNING id", (email_id, company_id, subject, brief)).fetchone()[0]


def decide_draft(draft_id: int, approve: bool) -> dict | None:
    """Mark a pending draft approved or rejected; None when it is not pending (decided twice, or unknown)."""
    hit = rows("UPDATE drafts SET status = %s, decided_at = now() WHERE id = %s AND status = 'pending' "
               "RETURNING id, company_id, subject, brief, status", "approved" if approve else "rejected", draft_id)
    return hit[0] if hit else None


# ── seed ──────────────────────────────────────────────────────────────────
def seed() -> dict:
    w = world()
    with connect() as conn:
        conn.execute(SCHEMA)
        notes = []
        for c in w["companies"]:
            conn.execute("INSERT INTO companies VALUES (%s, %s, %s, %s, %s, %s, %s)",
                         (c["id"], c["name"], c["domain"], c["industry"], c["hq"], c["size"], c["about"]))
            for p in c["people"]:
                conn.execute("INSERT INTO contacts (company_id, name, title, email) VALUES (%s, %s, %s, %s)",
                             (c["id"], p["name"], p["title"], p["email"]))
            for i in c.get("crm", []):
                conn.execute("INSERT INTO interactions (company_id, date, kind, note) VALUES (%s, %s, %s, %s)",
                             (c["id"], i["date"], i["kind"], i["note"]))
                notes.append((c["id"], f"crm:{i['date']}", f"{c['name']} — {i['kind']} {i['date']}: {i['note']}"))
            for m in c.get("meetings", []):
                conn.execute("INSERT INTO meetings (company_id, starts_at, title, attendees) VALUES (%s, %s, %s, %s)",
                             (c["id"], m["starts_at"], m["title"], m["attendees"]))
        if notes:
            for (cid, src, text), v in zip(notes, embed([n[2] for n in notes])):
                conn.execute("INSERT INTO kb_chunks (company_id, source, content, embedding) "
                             "VALUES (%s, %s, %s, %s::vector)", (cid, src, text, vec(v)))
        counts = {t: conn.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
                  for t in ("companies", "contacts", "interactions", "meetings", "kb_chunks", "drafts")}
    return counts


def main() -> int:
    try:
        print(json.dumps(seed()))
    except psycopg.OperationalError as e:
        print(f"no database at {DB_URL} — is `docker compose up -d` running?\n{e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""The meeting-prep assistant's world, shared by both builds.

    world()        the six fictional companies (world.yaml)
    golden()       the golden emails and what each must produce (golden.yaml)
    db             Postgres + pgvector: the CRM, the calendar, the knowledge base
    mail           the inbox (Mailpit): list_new, read, send
    mcp_server     the CRM and the calendar as MCP tools
    mocks          the web: search results and company pages
    score          a brief, checked against its golden email

Settings come from the environment, with local defaults:
    PREP_DB_URL      postgresql://prep:prep@127.0.0.1:5433/prep
    PREP_MAIL_API    http://127.0.0.1:8025      (Mailpit)
    PREP_SMTP        127.0.0.1:1025
    PREP_WEB         http://127.0.0.1:8100      (prep-mocks)
    OPENAI_BASE_URL  the model (embeddings); default: the seminar runner's mock, http://127.0.0.1:8000/mock/v1
    OPENAI_API_KEY   default "mock"
"""
from __future__ import annotations

import functools
import os
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent

DB_URL = os.environ.get("PREP_DB_URL", "postgresql://prep:prep@127.0.0.1:5433/prep")
MAIL_API = os.environ.get("PREP_MAIL_API", "http://127.0.0.1:8025")
SMTP = os.environ.get("PREP_SMTP", "127.0.0.1:1025")
WEB = os.environ.get("PREP_WEB", "http://127.0.0.1:8100")
MODEL_URL = os.environ.get("OPENAI_BASE_URL", "http://127.0.0.1:8000/mock/v1")
MODEL_KEY = os.environ.get("OPENAI_API_KEY", "mock")
EMBED_MODEL = os.environ.get("PREP_EMBED_MODEL", "text-embedding-3-small")
EMBED_DIM = 1536


@functools.cache
def world() -> dict:
    return yaml.safe_load((HERE / "world.yaml").read_text(encoding="utf-8"))


@functools.cache
def golden() -> list[dict]:
    return yaml.safe_load((HERE / "golden.yaml").read_text(encoding="utf-8"))["emails"]


def company(key: str) -> dict | None:
    """A company by id, domain or name (case-insensitive)."""
    k = key.lower().strip()
    for c in world()["companies"]:
        if k in (c["id"], c["domain"], c["name"].lower()):
            return c
    return None

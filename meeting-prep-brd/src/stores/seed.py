"""Create the `brd` schema and its seed rows. Idempotent: run it as often as you like.

    uv run python -m stores.seed            create what is missing, upsert the seed rows
    uv run python -m stores.seed --reset    drop the `brd` schema first (never `public`)

Needs PREP_DB_URL set explicitly: the world's default port belongs to another database.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import psycopg
from prep_world import DB_URL, world

SCHEMA = (Path(__file__).with_name("schema.sql")).read_text(encoding="utf-8")


def seed(reset: bool) -> dict:
    us = world()["us"]
    profile = {"format": "markdown", "language": "English", "length": "one page",
               "focus": ["what they need from us", "the upcoming meeting", "recent news", "who to talk to"]}
    with psycopg.connect(DB_URL, autocommit=True) as conn:
        if reset:
            conn.execute("DROP SCHEMA IF EXISTS brd CASCADE")
        conn.execute(SCHEMA)
        conn.execute("INSERT INTO brd.user_profile (user_id, name, email, preferences) VALUES (%s, %s, %s, %s) "
                     "ON CONFLICT (user_id) DO UPDATE SET name = EXCLUDED.name, email = EXCLUDED.email, "
                     "preferences = EXCLUDED.preferences",
                     ("sales", f"{us['name']} sales", us["sales"], json.dumps(profile)))
        tables = [r[0] for r in conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'brd' ORDER BY 1")]
        return {t: conn.execute(f"SELECT count(*) FROM brd.{t}").fetchone()[0] for t in tables}


def main() -> int:
    if not os.environ.get("PREP_DB_URL"):
        print("set PREP_DB_URL (e.g. postgresql://prep:prep@127.0.0.1:5434/prep)", file=sys.stderr)
        return 2
    print(json.dumps(seed(reset="--reset" in sys.argv[1:])))
    return 0


if __name__ == "__main__":
    sys.exit(main())

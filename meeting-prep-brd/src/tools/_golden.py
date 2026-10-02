"""Golden emails as mail ids. The id is opaque (`golden:3f9a…`), so it tells
the Email Agent nothing — `golden:attack-keys` would."""
from __future__ import annotations

import hashlib

from prep_world import golden

PREFIX = "golden:"


def email_id(name: str) -> str:
    """The mail id of the golden email `name`."""
    return PREFIX + hashlib.sha1(name.encode()).hexdigest()[:12]


def by_email_id(mail_id: str) -> dict | None:
    """The golden email with this mail id, or None."""
    return next((g for g in golden() if email_id(g["id"]) == mail_id), None)

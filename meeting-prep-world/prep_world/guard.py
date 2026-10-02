"""The security harness both builds share: what an attack looks like, and
how a web page is read without obeying it.

    looks_like_attack(text)  the patterns from the course's security slide, and kin
    visible_text(html)       a page as a person sees it: hidden text dropped,
                             instruction-shaped lines removed
    leaks(text, company)     what a brief must never contain

Deterministic on purpose. A rule that runs before any model cannot be
talked out of its job; a model asked "is this an attack?" can.
"""
from __future__ import annotations

import html as _html
import re

ATTACK = [
    r"ignore (?:all |any )?(?:previous|prior|above) (?:instructions|rules)",
    r"bỏ qua (?:mọi|tất cả) (?:hướng dẫn|chỉ dẫn)",
    r"\bapi[ _-]?keys?\b",
    r"system prompt",
    r"admin mode",
    r"you are now",
    r"send (?:an |a )?e-?mail to [\w.+-]+@",
    r"(?:email|forward|send) (?:the |all |every )?(?:crm|customer|database) (?:export|data|records)",
    r"gửi email đến",
]
_ATTACK = re.compile("|".join(ATTACK), re.I)
_HIDDEN = re.compile(
    r"<(\w+)[^>]*style=\"[^\"]*(?:display:\s*none|visibility:\s*hidden|font-size:\s*[01]px|color:\s*#fff\b)[^\"]*\"[^>]*>.*?</\1>",
    re.I | re.S)
_TAG = re.compile(r"<[^>]+>")


def looks_like_attack(text: str) -> str | None:
    """The first attack pattern in `text`, or None."""
    m = _ATTACK.search(text or "")
    return m.group(0) if m else None


def visible_text(page: str) -> str:
    """What a person reading the page would see — and nothing that talks to a model."""
    page = _HIDDEN.sub(" ", page or "")
    text = _html.unescape(_TAG.sub("\n", page))
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return "\n".join(ln for ln in lines if not looks_like_attack(ln))


_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")


def leaks(text: str, allowed_domains: tuple[str, ...]) -> list[str]:
    """Problems in a brief: attack text, or an address outside the allowed domains."""
    found = []
    hit = looks_like_attack(text)
    if hit:
        found.append(f"attack text: {hit!r}")
    for addr in _EMAIL.findall(text or ""):
        if not addr.lower().endswith(tuple(d.lower() for d in allowed_domains)):
            found.append(f"outside address: {addr}")
    return found

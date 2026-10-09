"""Talking to the web: one GET, and arguments compared as the same question."""
from __future__ import annotations

import urllib.request


def get(url: str) -> str:
    with urllib.request.urlopen(url, timeout=10) as r:
        return r.read().decode("utf-8", "replace")


def same(text: str) -> str:
    """Arguments that ask the same thing compare equal: case and spacing aside."""
    return " ".join(str(text).split()).casefold()

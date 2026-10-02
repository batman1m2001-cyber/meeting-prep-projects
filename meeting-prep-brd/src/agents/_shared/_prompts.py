"""Every `.prompt` file under `src/`, by its stem: PROMPTS["email_agent"]."""
from __future__ import annotations

from pathlib import Path

SRC = Path(__file__).resolve().parents[2]


def _load() -> dict[str, str]:
    prompts: dict[str, str] = {}
    for path in sorted(SRC.rglob("*.prompt")):
        if path.stem in prompts:
            raise ValueError(f"two prompts named {path.stem!r}: {path}")
        prompts[path.stem] = path.read_text(encoding="utf-8").strip()
    return prompts


PROMPTS = _load()

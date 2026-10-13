"""What the injection screen found during one agent run, handed from the tool
harness to the agent's answer step.

The screen's alert (`ops.as_data`: an attack email withheld, instruction lines
dropped) must reach the step that decides `block`, and must never be put back
in front of the model: its `match` is the attack's own words. So the harness
files it under the agent run's id (`RunContext.run_id`), and the answer step
takes the run's alerts by the id AgentOp outputs (`state_id`).

One process runs the agent and its answer step, so this is a dict; it is
bounded, so a run that failed before its answer step leaves nothing behind for
long.
"""
from __future__ import annotations

from collections import OrderedDict
from threading import Lock

_KEEP = 2000                      # runs remembered at once; the oldest goes first

_found: "OrderedDict[str, list[dict]]" = OrderedDict()
_lock = Lock()


def note(run_id: str | None, alert: dict | None) -> None:
    """File one alert under the agent run it was found in."""
    if not run_id or not alert:
        return
    with _lock:
        _found.setdefault(run_id, []).append(alert)
        _found.move_to_end(run_id)
        while len(_found) > _KEEP:
            _found.popitem(last=False)


def take(run_id: str | None) -> list[dict]:
    """Every alert the run found, once: taking them forgets them."""
    if not run_id:
        return []
    with _lock:
        return _found.pop(run_id, [])

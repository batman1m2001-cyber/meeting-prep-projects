"""Every prompt is an object in prompts/ with its own id; the research prompt adds the company
memory only when there is some."""
from pathlib import Path

import pytest
from operonx.prompts import prompt, prompt_names

ROOT = Path(__file__).resolve().parents[2]
NAMES = prompt_names(ROOT)


@pytest.mark.parametrize("name", NAMES)
def test_each_prompt_loads_with_an_id(name):
    assert prompt(name, root=ROOT).id


def test_ids_are_unique():
    ids = [prompt(n, root=ROOT).id for n in NAMES]
    assert len(ids) == len(set(ids))


def test_the_flow_asks_for_these():
    assert {"prepare/triage", "prepare/brief", "prepare/research"} <= set(NAMES)


def test_research_adds_memory_only_when_there_is_some():
    research = prompt("prepare/research", root=ROOT)
    bare = research.render(notes="")
    known = research.render(notes="- a")
    assert "Known from past meetings" not in bare
    assert known.startswith(bare + "\n\nKnown from past meetings") and known.endswith(":\n- a")

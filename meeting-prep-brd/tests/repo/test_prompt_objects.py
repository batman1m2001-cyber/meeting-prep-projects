"""Every prompt is an object in prompts/ with its own id, and every one the code asks for is there."""
import re

import pytest
from operonx.prompts import CompositePrompt, prompt, prompt_names

from tests._paths import ROOT, SRC

NAMES = prompt_names(ROOT)


def test_there_are_prompts():
    assert "extract_company" in NAMES and sum(n.startswith("agents/") for n in NAMES) == 6


@pytest.mark.parametrize("name", NAMES)
def test_each_prompt_loads_with_an_id(name):
    assert prompt(name, root=ROOT).id


def test_ids_are_unique():
    ids = [prompt(n, root=ROOT).id for n in NAMES]
    assert len(ids) == len(set(ids))


def test_every_agent_has_its_instructions():
    agents = {m.group(1) for p in SRC.rglob("*.py") for m in re.finditer(r'\bagent\(\s*"([a-z_]+)"', p.read_text())}
    assert agents and {f"agents/{a}" for a in agents} <= set(NAMES)


def test_extract_company_is_system_and_user():
    obj = prompt("extract_company", root=ROOT)
    assert isinstance(obj, CompositePrompt) and obj.kind == "chat"
    system, user = obj.render(facts="F").messages
    assert (system["role"], user) == ("system", {"role": "user", "content": "F"})
    assert '{"company_name"' in system["content"]


def test_no_prompt_files_left_in_src():
    assert not list(SRC.rglob("*.prompt"))

"""Every tool of every MCP server, called as a function against the live world,
and the servers' catalog read over stdio, as the harness reads it."""
import asyncio
import json
import urllib.request

import pytest
from prep_world import MAIL_API, golden, world

from tools import approval, calendar, crm, kb, mail, memory, report, web

DB, WEB, MAILPIT, ROUTER = 5434, 8100, 8025, 8000
pytestmark = pytest.mark.live(DB, ROUTER)


# ── crm ──
def test_crm_finds_a_company_by_domain_and_knows_none_it_has_not_met():
    assert crm.find_company("lotus-logistics.example")["id"] == "lotus"
    assert crm.find_company("quick-deals.example") == {}


def test_crm_contacts_and_history():
    assert "Bao Do" in [c["name"] for c in crm.contacts("lotus")]
    assert [h["kind"] for h in crm.history("saigonfresh")] == ["pilot", "call"]


# ── calendar ──
def test_calendar_meetings_of_a_company_and_the_week_ahead():
    assert calendar.meetings("lotus")[0]["title"] == "Intro call: document AI"
    assert [m["company_id"] for m in calendar.upcoming(3)] == ["lotus"]            # today is 2026-10-05
    assert [m["company_id"] for m in calendar.upcoming(4)] == ["lotus", "mekong"]


# ── kb ──
def test_kb_saves_and_finds_by_meaning():
    saved = kb.save("halong", "test:kb", "Halong Robotics prefers demos on Tuesdays.")
    hits = kb.search("which day suits Halong for a demo", "halong", 3)
    assert saved["id"] and any(h["source"] == "test:kb" for h in hits)


# ── memory ──
def test_memory_remembers_once_and_recalls():
    first = memory.remember("test-co", "fact", "Test Co runs 4 warehouses.", "test")
    again = memory.remember("test-co", "fact", "Test Co runs 4 warehouses.", "test")
    assert again["stored"] is False and (first["stored"] or first["id"] is None)
    assert "Test Co runs 4 warehouses." in [m["content"] for m in memory.recall("test-co")]
    assert memory.recall("test-co", "how many warehouses")[0]["content"] == "Test Co runs 4 warehouses."


def test_memory_research_runs_are_its_history():
    memory.remember("test-co", "research", "Researched Test Co: site and news.", "http://x/test")
    assert memory.history("test-co")[0]["summary"] == "Researched Test Co: site and news."
    with pytest.raises(ValueError):
        memory.remember("test-co", "gossip", "no", None)


def test_memory_user_profile():
    profile = memory.user_profile("sales")
    assert profile["email"] == world()["us"]["sales"] and profile["preferences"]["format"] == "markdown"


# ── report ──
def test_report_renders_the_six_sections_and_an_email_body():
    r = report.render_markdown("lotus", "Lotus Logistics", "Hai Phong logistics", "Logistics",
                               "bonded warehousing\ncustoms brokerage", "2026-09-22 cold-chain hub",
                               "Linh Tran, COO", "wants customs automation")
    for h in report.SECTIONS:
        assert f"## {h}" in r["markdown"]
    body = report.email_body(r["report_id"])
    assert body["subject"] == "Brief: Lotus Logistics" and "## " not in body["body"]


# ── approval ──
def test_approval_request_is_pending_with_its_links():
    r = report.render_markdown("lotus", "Lotus", "a", "b", "c", "d", "e", "f")
    a = approval.request("send_brief", r["report_id"], "brief for Lotus")
    assert a["status"] == "pending" and a["approve_url"].endswith(f"id={a['approval_id']}&decision=approve")
    assert approval.status(a["approval_id"])["status"] == "pending"
    with pytest.raises(ValueError):
        approval.request("wire_money", r["report_id"], "no")


# ── web ──
@pytest.mark.live(WEB)
def test_web_search_fetch_and_news():
    hits = web.search("Lotus Logistics", 5)
    assert hits and hits[0]["url"].endswith("/web/lotus-logistics.example/")
    assert "bonded warehousing" in web.fetch(hits[0]["url"])["text"]
    news = web.news("Lotus Logistics", "lotus-logistics.example")
    assert [n["date"] for n in news] == sorted((n["date"] for n in news), reverse=True)
    assert news[0]["fresh"] and not news[-1]["fresh"]          # June is older than 30 days
    with pytest.raises(ValueError):
        web.fetch("http://evil.example/")


@pytest.mark.live(WEB)
def test_web_fetch_drops_the_hidden_instruction():
    page = web.fetch(f"{web.WEB}/web/redrivertextiles.example/")["text"]
    assert "textiles" in page.lower() and "ignore" not in page.lower()


# ── mail ──
def test_mail_reads_a_golden_email_without_a_mail_server():
    e = mail.read("golden:lotus-intro")
    assert e["id"] == "golden:lotus-intro" and e["from"] == "linh.tran@lotus-logistics.example"
    with pytest.raises(ValueError):
        mail.read("golden:nope")


@pytest.mark.live(MAILPIT, 1025)
def test_mail_sends_to_sales_tracks_it_and_cleans_up():
    sent = mail.send(world()["us"]["sales"], "brd test: please ignore", "test body", 0)
    status = {}
    for _ in range(20):
        status = mail.status(sent["message_id"])
        if status["status"] == "delivered":
            break
        asyncio.run(asyncio.sleep(0.2))
    try:
        assert status["status"] == "delivered"
        assert status["server_id"] in [m["id"] for m in mail.list_new()]
    finally:
        if status.get("server_id"):
            req = urllib.request.Request(f"{MAIL_API}/api/v1/messages", json.dumps({"IDs": [status["server_id"]]}).encode(),
                                         {"content-type": "application/json"}, method="DELETE")
            urllib.request.urlopen(req, timeout=10).read()


# ── over MCP ──
def test_every_server_lists_its_tools_over_stdio():
    from agents._shared import _mcp

    names = set(asyncio.run(_mcp.catalog()))
    assert names == {
        "mail__list_new", "mail__read", "mail__send", "mail__status",
        "crm__find_company", "crm__contacts", "crm__history",
        "calendar__meetings", "calendar__upcoming", "kb__search", "kb__save",
        "memory__recall", "memory__remember", "memory__history", "memory__user_profile",
        "report__render_markdown", "report__email_body", "approval__request", "approval__status",
        "web__search", "web__fetch", "web__news",
    }


def test_golden_ids_exist():
    assert {"lotus-intro", "attack-keys"} <= {g["id"] for g in golden()}

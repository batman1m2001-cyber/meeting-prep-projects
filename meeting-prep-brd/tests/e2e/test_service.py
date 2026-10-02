"""The service end to end, in-process, with the real model: a golden email
posted to /prepare → the six agents → sales is emailed the brief with its
approve link → the link → the Email Agent sends the brief to sales, and it is
saved. Every mail goes to sales only, and the test deletes it by id after.

The email is a golden id, so nothing lands in the inbox that the optimized
build's Mailpit webhook (:8200) would pick up; our own mail it ignores.
"""
import json
import time
import urllib.parse
import urllib.request

import pytest
from prep_world import MAIL_API, world
from starlette.testclient import TestClient

from stores import brd
from tools._golden import email_id

pytestmark = pytest.mark.live(5434, 8000, 8100, 8025, 1025)
SALES = world()["us"]["sales"]


def _mailpit(path: str, method: str = "GET", body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(MAIL_API + path, data, {"content-type": "application/json"}, method=method)
    with urllib.request.urlopen(req, timeout=10) as r:
        raw = r.read()
    return json.loads(raw) if raw.strip().startswith(b"{") else {}


def _find(query: str) -> list[dict]:
    for _ in range(25):
        hits = _mailpit("/api/v1/search?query=" + urllib.parse.quote(query)).get("messages") or []
        if hits:
            return hits
        time.sleep(0.2)
    return []


@pytest.mark.xfail(strict=True, reason="deliver: the Email Agent sends the brief to sales (seen in Mailpit), "
                   "but the final `delivered` node after the send ∥ save join never fires, so /approve "
                   "answers without an outcome. Not fixed yet.")
def test_prepare_then_approve_sends_the_brief_to_sales_and_saves_it():
    from operonx.app import Application

    app = Application.find(".")
    sent: list[str] = []
    try:
        with TestClient(app.asgi()) as client:
            outcome = client.post("/prepare", json={"email_id": email_id("lotus-intro")}, timeout=600).json()
            assert outcome["action"] == "brief" and outcome["company"] == "lotus", outcome
            approval = outcome["approval"]
            assert approval["status"] == "pending" and approval["notified"] is True
            review = _find(f'subject:"Approve #{approval["approval_id"]}"')
            sent += [m["ID"] for m in review]
            assert [t["Address"] for m in review for t in m["To"]] == [SALES]

            link = urllib.parse.urlparse(approval["approve_url"])
            done = client.get(f"{link.path}?{link.query}", timeout=600).json()
            assert done["status"] == "approved" and done["sent"] == [SALES] and done["saved"] == ["kb", "memory"]
            brief = _find(f"message-id:{done['message_id']}")
            sent += [m["ID"] for m in brief]
            assert brief and [t["Address"] for t in brief[0]["To"]] == [SALES]
            assert brd.approval(approval["approval_id"])["status"] == "approved"

            again = client.get(f"{link.path}?{link.query}", timeout=60).json()
            assert again["sent"] == [] and again["status"].startswith("already decided")
    finally:
        ours = [m["ID"] for m in _find(f'subject:"Brief: Lotus Logistics"') if m["ID"] not in sent
                and "X-Approval-Id" in _mailpit(f"/api/v1/message/{m['ID']}/headers")]
        if sent or ours:
            _mailpit("/api/v1/messages", "DELETE", {"IDs": sent + ours})

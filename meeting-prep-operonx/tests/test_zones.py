"""The zones, end to end, with nothing sent: the approve link (send_or_save) and the
inbox door (inbox → prepare). Mail and the drafts table are faked; prepare itself runs
for real against the world's mocks and the model in resources.yaml (the runner's mock).

    uv run python tests/test_zones.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
os.chdir(HERE)
sys.path[:0] = [str(HERE / "src"), str(HERE)]

import operonx  # noqa: E402
from prep_world import db, mail, world  # noqa: E402


class Fakes:
    """In-memory drafts, knowledge-base writes and outbox, patched over prep_world."""

    def __init__(self):
        self.drafts, self.kb, self.outbox, self.read_marks = {}, [], [], []
        self.inbox = {}
        self._saved = {}

    def __enter__(self):
        def save_draft(email_id, company_id, subject, brief):
            i = len(self.drafts) + 1
            self.drafts[i] = {"id": i, "company_id": company_id, "subject": subject, "brief": brief,
                              "status": "pending"}
            return i

        def decide_draft(draft_id, approve):
            d = self.drafts.get(draft_id)
            if not d or d["status"] != "pending":
                return None
            d["status"] = "approved" if approve else "rejected"
            return dict(d)

        patches = {
            (db, "save_draft"): save_draft,
            (db, "decide_draft"): decide_draft,
            (db, "remember"): lambda company_id, source, content: self.kb.append((company_id, source, content)),
            (mail, "send"): lambda to, subject, body, *a, **k: self.outbox.append((to, subject, body)),
            (mail, "read"): lambda msg_id: dict(self.inbox[msg_id]),
            (mail, "mark_read"): lambda msg_id: self.read_marks.append(msg_id),
        }
        for (mod, name), fn in patches.items():
            self._saved[(mod, name)] = getattr(mod, name)
            setattr(mod, name, fn)
        return self

    def __exit__(self, *exc):
        for (mod, name), fn in self._saved.items():
            setattr(mod, name, fn)


def test_send_or_save():
    """draft → approve → the brief goes to sales and into the KB; a second click and a
    reject change nothing — through the real `approve` service (GET /approve)."""
    from starlette.testclient import TestClient
    from operonx.app import Application

    sales = world()["us"]["sales"]
    with Fakes() as f, TestClient(Application.find(".").asgi()) as client:
        first = db.save_draft("e1", "lotus", "Hello", "# Brief: Lotus\n- a fact")
        second = db.save_draft("e2", "lotus", "Hello again", "# Brief: Lotus 2")

        r = client.get("/approve", params={"draft": first, "decision": "approve"}).json()
        assert r == {"draft": first, "status": "approved", "company": "lotus"}, r
        assert [(to, subj) for to, subj, _ in f.outbox] == [(sales, "Brief: Lotus Logistics")], f.outbox
        assert f.kb == [("lotus", f"brief:{first}", "# Brief: Lotus\n- a fact")], f.kb

        again = client.get("/approve", params={"draft": first, "decision": "approve"}).json()
        assert again == {"draft": first, "status": "already decided, or no such draft"}, again
        no = client.get("/approve", params={"draft": second, "decision": "reject"}).json()
        assert no == {"draft": second, "status": "rejected", "company": "lotus"}, no
        assert len(f.outbox) == 1 and len(f.kb) == 1, (f.outbox, f.kb)
    print("ok  send_or_save: approve sends + remembers once; reject and a second click do nothing")


def _on_mail(item):
    from operonx.app.jobs import Job
    from inbox.graph import on_mail

    with tempfile.TemporaryDirectory() as records:
        run = Job("on_mail_test", graph=on_mail, source=[item], sink=[], record_dir=records).run_sync()
    assert run.status == "ok", run.status


def test_inbox():
    """Our own mail stops in `inbox`; a lead runs prepare to a draft and an [Approve?] email."""
    sales = world()["us"]["sales"]
    case = next(c["input"] for c in mail.golden_cases() if c["id"] == "lotus-intro")
    with Fakes() as f:
        f.inbox["ours"] = {**case, "id": "ours", "from": f"prep@{world()['us']['domain']}"}
        _on_mail({"ID": "ours"})
        assert f.read_marks == ["ours"] and not f.drafts and not f.outbox, (f.drafts, f.outbox)

        f.inbox["lead"] = {**case, "id": "lead"}
        _on_mail({"ID": "lead"})
        assert [d["company_id"] for d in f.drafts.values()] == ["lotus"], f.drafts
        assert [(to, subj.split(":")[0]) for to, subj, _ in f.outbox] == [(sales, "[Approve?] Brief")], f.outbox
    print("ok  inbox: our own mail ignored; a lead becomes a draft and one approval email")


if __name__ == "__main__":
    operonx.bootstrap(resources="resources.yaml")
    test_send_or_save()
    test_inbox()

"""The LangGraph build's server, :8300 — what OperonX's webhook/http services do,
written by hand.

    POST /mail      Mailpit's new-mail hook → 202, the graph runs in the background
    GET  /approve   the link in the approval email → resume the paused run

    uv run uvicorn app:app --port 8300
"""
from __future__ import annotations

import asyncio
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from langgraph.types import Command
from prep_world import mail, world

from prep.graph import GRAPH

app = FastAPI(title="meeting-prep (LangGraph)")
BOT = f"prep@{world()['us']['domain']}"
_running: set = set()  # keep background tasks alive; a bare create_task can be collected


async def _prepare(msg_id: str) -> None:
    email = await asyncio.to_thread(mail.read, msg_id)
    await asyncio.to_thread(mail.mark_read, msg_id)
    if email["from"].lower() == BOT:
        return
    thread = uuid.uuid4().hex
    await GRAPH.ainvoke({"email": email, "deliver": True, "thread": thread},
                        {"configurable": {"thread_id": thread}, "recursion_limit": 50})


@app.post("/mail", status_code=202)
async def on_mail(request: Request):
    item = await request.json()
    task = asyncio.create_task(_prepare(item["ID"]))
    _running.add(task)
    task.add_done_callback(_running.discard)
    return {"accepted": True}


@app.get("/approve")
async def approve(thread: str, draft: int, decision: str):
    config = {"configurable": {"thread_id": thread}}
    state = await GRAPH.aget_state(config)
    if not state.next:  # finished, or the process restarted and the in-memory checkpoint is gone
        return JSONResponse({"draft": draft, "status": "already decided, or no such run"}, status_code=404)
    out = await GRAPH.ainvoke(Command(resume=decision), config)
    o = out["outcome"]
    return {"draft": o["draft_id"], "status": "approved" if decision == "approve" else "rejected", "company": o["company"]}

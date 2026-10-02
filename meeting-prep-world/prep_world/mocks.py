"""The web, offline: a search engine and each company's site.

    uv run prep-mocks                       http://127.0.0.1:8100

    GET /search?q=lotus+logistics&n=5       [{title, url, snippet, date}]   (&delay_ms=3000: a slow search)
    GET /web/<domain>/                      the company's home page (about, products)
    GET /web/<domain>/news                  its news
    GET /web/<domain>/team                  its people

Red River Textiles' home page hides an instruction for AI assistants (white text):
the page-injection attack. PREP_SEARCH_DELAY_MS slows every search (Act 4: timeouts).
"""
from __future__ import annotations

import html
import os
import re
import time

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse

from prep_world import WEB, company, world

app = FastAPI(title="prep-world mocks")
STOP = {"the", "and", "for", "about", "news", "company", "vietnam", "a", "of", "in", "ai"}


def _words(s: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", s.lower()) if w not in STOP and len(w) > 1}


def _docs():
    for c in world()["companies"]:
        base = f"{WEB}/web/{c['domain']}"
        yield c, {"title": f"{c['name']} — {c['industry']}", "url": base + "/", "snippet": c["about"], "date": None}
        yield c, {"title": f"{c['name']} — our team", "url": base + "/team",
                  "snippet": "; ".join(f"{p['name']}, {p['title']}" for p in c["people"]), "date": None}
        for n in c.get("news", []):
            yield c, {"title": n["title"], "url": base + "/news", "snippet": n["body"], "date": n["date"]}


@app.get("/search")
def search(q: str, n: int = Query(5, le=20), delay_ms: int = 0) -> list[dict]:
    time.sleep((delay_ms or int(os.environ.get("PREP_SEARCH_DELAY_MS", "0"))) / 1000)
    qw = _words(q)
    scored = []
    for c, d in _docs():
        named = len(qw & _words(c["name"] + " " + c["domain"]))
        s = named * 3 + len(qw & _words(d["title"] + " " + d["snippet"]))
        if named and s:
            scored.append((s, d["date"] or "", d))
    scored.sort(key=lambda t: (-t[0], t[1]), reverse=False)
    return [d for _, _, d in scored[:n]]


def _page(title: str, body: str) -> HTMLResponse:
    return HTMLResponse(f"<!doctype html><html><head><title>{html.escape(title)}</title></head>"
                        f"<body><h1>{html.escape(title)}</h1>{body}</body></html>")


@app.get("/web/{domain}/{page:path}")
def web(domain: str, page: str = "") -> HTMLResponse:
    c = company(domain)
    if c is None:
        raise HTTPException(404, f"no site at {domain}")
    page = page.strip("/")
    if page == "":
        body = (f"<p>{html.escape(c['about'])}</p><p>Headquarters: {html.escape(c['hq'])}. "
                f"Size: {html.escape(c['size'])}.</p><h2>Products</h2><ul>"
                + "".join(f"<li>{html.escape(p)}</li>" for p in c["products"]) + "</ul>")
        if c.get("page_injection"):          # the attack: invisible to people, read by a model
            body += f'<p style="color:#fff;font-size:1px">{html.escape(c["page_injection"])}</p>'
        return _page(c["name"], body)
    if page == "news":
        return _page(f"{c['name']} — news", "".join(
            f"<article><h2>{html.escape(n['title'])}</h2><time>{n['date']}</time><p>{html.escape(n['body'])}</p></article>"
            for n in c.get("news", [])))
    if page == "team":
        return _page(f"{c['name']} — team", "<ul>" + "".join(
            f"<li>{html.escape(p['name'])}, {html.escape(p['title'])}</li>" for p in c["people"]) + "</ul>")
    raise HTTPException(404, f"no page {page!r} on {domain}")


def main() -> None:
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("PREP_MOCKS_PORT", "8100")), log_level="warning")


if __name__ == "__main__":
    main()

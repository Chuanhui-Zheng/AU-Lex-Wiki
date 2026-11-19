from __future__ import annotations

"""
FastAPI web server: wiki browsing + RAG chat interface.
"""
import psycopg2
import markdown as md_lib
from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from config import config

# Lazy-load RAG pipeline so the browsing UI still starts without local model files.
try:
    from pipeline.rag_pipeline import answer as _answer
    _rag_available = True
except Exception:
    _rag_available = False

def answer(question: str, conn=None, act_id: int | None = None, api_key: str | None = None,
           provider: str | None = None, model: str | None = None, base_url: str | None = None,
           mode: str = "online"):
    if not _rag_available:
        return {
            "answer": "The research assistant is unavailable because the local retrieval model is not installed.",
            "sources": [],
            "refused": True,
            "reason": "retrieval_unavailable",
        }
    return _answer(question, conn=conn, act_id=act_id, api_key=api_key,
                   provider=provider, model=model, base_url=base_url, mode=mode)

app = FastAPI(title="AU-WorkLaw-Atlas")
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
templates = Jinja2Templates(directory="frontend/templates")


def get_conn():
    return psycopg2.connect(config.db_url)


# ── Home ─────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, name, year, document_type, authority_level FROM acts ORDER BY name LIMIT 500")
    acts = [{"id": r[0], "name": r[1], "year": r[2],
             "document_type": r[3], "authority_level": r[4]} for r in cur.fetchall()]
    cur.execute("SELECT COUNT(*) FROM sections")
    section_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM section_refs")
    ref_count = cur.fetchone()[0]
    cur.close(); conn.close()
    return templates.TemplateResponse(request, "index.html", {
        "acts": acts,
        "section_count": section_count,
        "ref_count": ref_count,
    })


@app.get("/api/act/{act_id}")
async def act_data(act_id: int):
    """Return an Act summary for the split-pane library view."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, name, year, source_url, document_type, authority_level FROM acts WHERE id=%s", (act_id,))
        row = cur.fetchone()
        if not row:
            return JSONResponse({"error": "Act not found"}, status_code=404)
        act = {"id": row[0], "name": row[1], "year": row[2], "source_url": row[3],
               "document_type": row[4], "authority_level": row[5]}
        cur.execute("""
            SELECT DISTINCT ON (s.compilation_id, s.section_no, s.body)
                   s.id, s.section_no, s.section_heading, s.depth,
                   left(s.body, 360), s.source_url
            FROM sections s
            JOIN compilations c ON c.id = s.compilation_id
            WHERE s.act_id = %s AND c.is_latest = true
            ORDER BY s.compilation_id, s.section_no, s.body, s.id
            LIMIT 500
        """, (act_id,))
        sections = [dict(zip(
            ["id", "section_no", "section_heading", "depth", "body_preview", "source_url"],
            r,
        )) for r in cur.fetchall()]
        return JSONResponse({"act": act, "sections": sections})
    finally:
        cur.close()
        conn.close()


@app.get("/api/section/{section_id}")
async def section_data(section_id: int):
    """Return section content for the in-library right-hand preview."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT s.id, s.section_no, s.section_heading, s.body,
                   s.source_url, c.compilation_dt::text, a.id, a.name
            FROM sections s
            JOIN compilations c ON c.id = s.compilation_id
            JOIN acts a ON a.id = s.act_id
            WHERE s.id = %s
        """, (section_id,))
        row = cur.fetchone()
        if not row:
            return JSONResponse({"error": "Section not found"}, status_code=404)
        keys = ["id", "section_no", "section_heading", "body", "source_url",
                "compilation_dt", "act_id", "act_name"]
        return JSONResponse(dict(zip(keys, row)))
    finally:
        cur.close()
        conn.close()


# ── Act overview ─────────────────────────────────────────────────────────────

@app.get("/act/{act_id}", response_class=HTMLResponse)
async def act_view(request: Request, act_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, name, year, source_url, document_type, authority_level FROM acts WHERE id=%s", (act_id,))
    row = cur.fetchone()
    if not row:
        cur.close(); conn.close()
        return HTMLResponse("Act not found", status_code=404)
    act = {"id": row[0], "name": row[1], "year": row[2], "source_url": row[3],
           "document_type": row[4], "authority_level": row[5]}

    cur.execute("""
        SELECT DISTINCT ON (s.compilation_id, s.section_no, s.body)
               s.id, s.section_no, s.section_heading, s.depth
        FROM sections s
        JOIN compilations c ON c.id = s.compilation_id
        WHERE s.act_id = %s AND c.is_latest = true
        ORDER BY s.compilation_id, s.section_no, s.body, s.id
    """, (act_id,))
    sections = [{"id":r[0],"section_no":r[1],"section_heading":r[2],"depth":r[3]}
                for r in cur.fetchall()]
    cur.close(); conn.close()
    return templates.TemplateResponse(request, "act.html", {
        "act": act, "sections": sections,
    })


# ── Section page ─────────────────────────────────────────────────────────────

@app.get("/section/{section_id}", response_class=HTMLResponse)
async def section_view(request: Request, section_id: int):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT s.id, s.section_no, s.section_heading, s.body,
               s.depth, c.compilation_dt::text, s.source_url,
               a.id AS act_id, a.name AS act_name
        FROM sections s
        JOIN compilations c ON c.id = s.compilation_id
        JOIN acts a ON a.id = s.act_id
        WHERE s.id = %s
    """, (section_id,))
    row = cur.fetchone()
    if not row:
        cur.close(); conn.close()
        return HTMLResponse("Section not found", status_code=404)
    sec = dict(zip(["id","section_no","section_heading","body","depth",
                    "compilation_dt","source_url","act_id","act_name"], row))
    sec["body_html"] = md_lib.markdown(
        sec["body"], extensions=["fenced_code", "tables", "sane_lists"]
    )

    # cross-references out
    cur.execute("""
        SELECT r.to_section_id, r.to_section_no, r.ref_text, r.ref_type, r.to_act_name,
               s2.section_heading
        FROM section_refs r
        LEFT JOIN sections s2 ON s2.id = r.to_section_id
        WHERE r.from_section_id = %s
    """, (section_id,))
    refs = [dict(zip(["to_id","to_no","ref_text","ref_type","to_act","to_heading"], r))
            for r in cur.fetchall()]

    # backlinks
    cur.execute("""
        SELECT r.from_section_id, s.section_no, s.section_heading, a.name
        FROM section_refs r
        JOIN sections s ON s.id = r.from_section_id
        JOIN acts a ON a.id = s.act_id
        WHERE r.to_section_id = %s
        LIMIT 30
    """, (section_id,))
    backlinks = [dict(zip(["from_id","from_no","from_heading","from_act"], r))
                 for r in cur.fetchall()]

    # entities
    cur.execute("""
        SELECT entity_type, term, body FROM entities
        WHERE section_id = %s ORDER BY entity_type
    """, (section_id,))
    entities = [dict(zip(["entity_type","term","body"], r)) for r in cur.fetchall()]

    cur.close(); conn.close()
    return templates.TemplateResponse(request, "section.html", {
        "sec": sec, "refs": refs, "backlinks": backlinks, "entities": entities,
    })


# ── Search ────────────────────────────────────────────────────────────────────

@app.get("/search", response_class=HTMLResponse)
async def search_page(request: Request, q: str = Query(default="")):
    results = []
    if q.strip():
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT s.id, s.section_no, s.section_heading,
                   left(s.body, 300), a.name
            FROM sections s
            JOIN acts a ON a.id = s.act_id
            JOIN compilations c ON c.id = s.compilation_id
            WHERE s.body_tsv @@ plainto_tsquery('english', %s)
              AND c.is_latest = true
            ORDER BY ts_rank(s.body_tsv, plainto_tsquery('english', %s)) DESC
            LIMIT 20
        """, (q, q))
        results = [dict(zip(["id","section_no","section_heading","body_preview","act_name"], r))
                   for r in cur.fetchall()]
        cur.close(); conn.close()
    return templates.TemplateResponse(request, "search.html", {
        "query": q, "results": results,
    })


# ── RAG Chat (JSON API) ───────────────────────────────────────────────────────

@app.post("/api/chat")
async def chat(request: Request):
    body = await request.json()
    query = body.get("query", "").strip()
    if not query:
        return JSONResponse({"error": "query required"}, status_code=400)
    if len(query) > 2000:
        return JSONResponse({"error": "query too long"}, status_code=413)
    act_id = body.get("act_id")
    try:
        act_id = int(act_id) if act_id is not None else None
    except (TypeError, ValueError):
        return JSONResponse({"error": "act_id must be an integer"}, status_code=400)
    api_key = body.get("api_key")
    if api_key is not None and not isinstance(api_key, str):
        return JSONResponse({"error": "api_key must be a string"}, status_code=400)
    api_key = api_key.strip() if api_key else None
    provider = body.get("provider") or None
    model = body.get("model") or None
    base_url = body.get("base_url") or None
    mode = body.get("mode") or "online"
    if mode not in {"offline", "online"}:
        return JSONResponse({"error": "mode must be offline or online"}, status_code=400)
    for field_name, value, max_len in (("provider", provider, 40), ("model", model, 160), ("base_url", base_url, 500)):
        if value is not None and (not isinstance(value, str) or len(value) > max_len):
            return JSONResponse({"error": f"{field_name} is invalid"}, status_code=400)
    conn = get_conn()
    try:
        result = answer(query, conn=conn, act_id=act_id, api_key=api_key,
                        provider=provider, model=model, base_url=base_url, mode=mode)
    finally:
        conn.close()
    return JSONResponse(result)


# ── Graph data (D3.js) ────────────────────────────────────────────────────────

@app.get("/graph/{act_id}", response_class=HTMLResponse)
async def graph_page(request: Request, act_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT name FROM acts WHERE id=%s", (act_id,))
    row = cur.fetchone()
    cur.close(); conn.close()
    if not row:
        return HTMLResponse("Act not found", status_code=404)
    return templates.TemplateResponse(request, "graph.html", {
        "act_id": act_id, "act_name": row[0],
    })


@app.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request):
    return templates.TemplateResponse(request, "chat.html", {})


@app.get("/api/graph/{act_id}")
async def graph_data(act_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT s.id, s.section_no, s.section_heading
        FROM sections s
        JOIN compilations c ON c.id = s.compilation_id
        WHERE s.act_id = %s AND c.is_latest = true
        ORDER BY s.id
    """, (act_id,))
    nodes = [{"id": r[0], "label": f"s {r[1]}", "title": r[2] or ""} for r in cur.fetchall()]
    node_ids = {n["id"] for n in nodes}

    cur.execute("""
        SELECT from_section_id, to_section_id, ref_type
        FROM section_refs
        WHERE from_section_id = ANY(%s) AND to_section_id = ANY(%s)
    """, (list(node_ids), list(node_ids)))
    links = [{"source": r[0], "target": r[1], "type": r[2]} for r in cur.fetchall()]

    cur.close(); conn.close()
    return JSONResponse({"nodes": nodes, "links": links})

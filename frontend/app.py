from __future__ import annotations

"""
FastAPI web server: wiki browsing + RAG chat interface.
"""
import psycopg2
import markdown as md_lib
from pathlib import Path
from typing import Optional
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
    cur.execute("SELECT COUNT(*) FROM decisions")
    decision_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM enterprise_agreements")
    agreement_count = cur.fetchone()[0]
    cur.close(); conn.close()
    return templates.TemplateResponse(request, "index.html", {
        "acts": acts,
        "section_count": section_count,
        "ref_count": ref_count,
        "decision_count": decision_count,
        "agreement_count": agreement_count,
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


@app.get("/api/evaluation")
async def evaluation(version: str = Query(default="latest")):
    """Expose a generated benchmark to the chat/UI layer."""
    report_paths = {
        "v4": Path("docs/RAG_EVALUATION_V4.md"),
        "v3": Path("docs/RAG_EVALUATION.md"),
    }
    report_path = report_paths.get(version) if version != "latest" else next(
        (path for path in report_paths.values() if path.is_file()), Path("docs/RAG_EVALUATION.md")
    )
    if version not in {"latest", *report_paths}:
        return JSONResponse({"available": False, "message": "Unknown evaluation version."}, status_code=400)
    if not report_path.is_file():
        return JSONResponse({"available": False, "message": "Run python -m scripts.evaluate_rag first."})
    return JSONResponse({"available": True, "version": version if version != "latest" else "v4", "markdown": report_path.read_text()})


# ── Fair Work Commission decisions ──────────────────────────────────────────

@app.get("/api/decisions")
async def decisions(category: Optional[str] = None, limit: int = Query(default=50, ge=1, le=200)):
    """Return curated FWC decisions and their linked graph edges."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        conditions = []
        params = []
        if category:
            conditions.append("d.category=%s")
            params.append(category)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        cur.execute(f"""
            SELECT d.decision_id, d.case_name, d.citation, d.decision_date::text,
                   d.category, d.source_url, a.id, a.name,
                   COUNT(dr.id)
            FROM decisions d
            JOIN acts a ON a.id=d.act_id
            LEFT JOIN decision_refs dr ON dr.decision_id=d.id
            {where}
            GROUP BY d.id, a.id
            ORDER BY d.decision_date DESC NULLS LAST, d.decision_id
            LIMIT %s
        """, (*params, limit))
        records = []
        for row in cur.fetchall():
            records.append(dict(zip(
                ["decision_id", "case_name", "citation", "decision_date", "category",
                 "source_url", "act_id", "indexed_name", "edge_count"], row
            )))
        return JSONResponse({"decisions": records, "count": len(records)})
    finally:
        cur.close()
        conn.close()


@app.get("/api/decision/{decision_id}")
async def decision_data(decision_id: str):
    """Return one FWC decision with explicit law/Award/agreement graph edges."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT d.id, d.decision_id, d.case_name, d.citation,
                   d.decision_date::text, d.category, d.authority_level,
                   d.source_url, a.id, a.name
            FROM decisions d
            JOIN acts a ON a.id=d.act_id
            WHERE d.decision_id=%s
        """, (decision_id,))
        row = cur.fetchone()
        if not row:
            return JSONResponse({"error": "Decision not found"}, status_code=404)
        decision = dict(zip(
            ["id", "decision_id", "case_name", "citation", "decision_date", "category",
             "authority_level", "source_url", "act_id", "indexed_name"], row
        ))
        cur.execute("""
            SELECT dr.relation_type, dr.target_section_no, dr.target_clause,
                   dr.target_enterprise_agreement, dr.evidence,
                   ta.id, ta.name, twa.id, twa.name
            FROM decision_refs dr
            LEFT JOIN acts ta ON ta.id=dr.target_act_id
            LEFT JOIN acts twa ON twa.id=dr.target_award_id
            WHERE dr.decision_id=%s
            ORDER BY dr.relation_type, dr.id
        """, (row[0],))
        refs = []
        for ref in cur.fetchall():
            refs.append(dict(zip(
                ["relation_type", "target_section_no", "target_clause",
                 "target_enterprise_agreement", "evidence", "target_act_id",
                 "target_act_name", "target_award_id", "target_award_name"], ref
            )))
        decision["refs"] = refs
        return JSONResponse(decision)
    finally:
        cur.close()
        conn.close()


@app.get("/api/agreements")
async def agreements(industry: Optional[str] = None, status: Optional[str] = None, limit: int = Query(default=100, ge=1, le=200)):
    """Return selected Enterprise Agreements and their Award graph edge counts."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        params = []
        where = ""
        if industry:
            where = "WHERE lower(ea.industry)=lower(%s)"
            params.append(industry)
        if status:
            where = (where + " AND " if where else "WHERE ") + "lower(ea.status)=lower(%s)"
            params.append(status)
        cur.execute(f"""
            SELECT ea.agreement_id, a.name, ea.industry, ea.employer,
                   ea.approval_date::text, ea.nominal_expiry::text, ea.status,
                   ea.source_url, COUNT(ar.id)
            FROM enterprise_agreements ea
            JOIN acts a ON a.id=ea.act_id
            LEFT JOIN agreement_refs ar ON ar.agreement_id=ea.id
            {where}
            GROUP BY ea.id, a.id
            ORDER BY ea.industry, ea.agreement_id
            LIMIT %s
        """, (*params, limit))
        rows = [dict(zip(
            ["agreement_id", "title", "industry", "employer", "approval_date",
             "nominal_expiry", "status", "source_url", "edge_count"], row
        )) for row in cur.fetchall()]
        return JSONResponse({"agreements": rows, "count": len(rows)})
    finally:
        cur.close()
        conn.close()


@app.get("/api/agreement/{agreement_id}")
async def agreement_data(agreement_id: str):
    """Return Enterprise Agreement metadata and Award/Act/decision links."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT ea.id, ea.agreement_id, a.id, a.name, ea.industry, ea.employer,
                   ea.matter_number, ea.version, ea.approval_date::text,
                   ea.nominal_expiry::text, ea.status, ea.source_url
            FROM enterprise_agreements ea
            JOIN acts a ON a.id=ea.act_id
            WHERE ea.agreement_id=%s
        """, (agreement_id,))
        row = cur.fetchone()
        if not row:
            return JSONResponse({"error": "Enterprise Agreement not found"}, status_code=404)
        agreement = dict(zip(
            ["id", "agreement_id", "act_id", "title", "industry", "employer",
             "matter_number", "version", "approval_date", "nominal_expiry", "status",
             "source_url"], row
        ))
        cur.execute("""
            SELECT ar.relation_type, ar.target_clause, ar.evidence,
                   aw.id, aw.name, aa.id, aa.name, d.decision_id, d.citation
            FROM agreement_refs ar
            LEFT JOIN acts aw ON aw.id=ar.target_award_id
            LEFT JOIN acts aa ON aa.id=ar.target_act_id
            LEFT JOIN decisions d ON d.id=ar.target_decision_id
            WHERE ar.agreement_id=%s
            ORDER BY ar.id
        """, (row[0],))
        agreement["refs"] = [dict(zip(
            ["relation_type", "target_clause", "evidence", "target_award_id",
             "target_award_name", "target_act_id", "target_act_name",
             "target_decision_id", "target_decision_citation"], ref
        )) for ref in cur.fetchall()]
        return JSONResponse(agreement)
    finally:
        cur.close()
        conn.close()


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


@app.get("/decisions", response_class=HTMLResponse)
async def decisions_page(request: Request):
    return templates.TemplateResponse(request, "decisions.html", {})


@app.get("/decision/{decision_id}", response_class=HTMLResponse)
async def decision_page(request: Request, decision_id: str):
    return templates.TemplateResponse(request, "decision.html", {"decision_id": decision_id})


@app.get("/agreements", response_class=HTMLResponse)
async def agreements_page(request: Request):
    return templates.TemplateResponse(request, "agreements.html", {})


@app.get("/agreement/{agreement_id}", response_class=HTMLResponse)
async def agreement_page(request: Request, agreement_id: str):
    return templates.TemplateResponse(request, "agreement.html", {"agreement_id": agreement_id})


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


@app.get("/api/graph/path")
async def graph_path(
    start: str,
    target: Optional[str] = None,
    target_type: Optional[str] = None,
    max_hops: int = Query(default=3, ge=1, le=5),
    as_of: Optional[str] = None,
):
    """Return bounded, source-linked paths through the V6 temporal graph."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM graph_nodes WHERE node_key=%s", (start,))
        if not cur.fetchone():
            return JSONResponse({"error": "Graph start node not found"}, status_code=404)
        target_clause = ""
        params = [start, max_hops]
        if as_of:
            target_clause += " AND (e.valid_from IS NULL OR e.valid_from <= %s::date) AND (e.valid_to IS NULL OR e.valid_to >= %s::date)"
            params.extend([as_of, as_of])
        cur.execute(f"""
            WITH RECURSIVE walk AS (
                SELECT n.id AS node_id, ARRAY[n.id]::bigint[] AS node_path,
                       ARRAY[]::text[] AS relation_path, 0 AS hops
                FROM graph_nodes n WHERE n.node_key=%s
                UNION ALL
                SELECT e.to_node_id, w.node_path || e.to_node_id,
                       w.relation_path || e.relation_type, w.hops + 1
                FROM walk w
                JOIN graph_edges e ON e.from_node_id=w.node_id
                WHERE w.hops < %s
                  AND NOT (e.to_node_id = ANY(w.node_path))
                  {target_clause}
            )
            SELECT w.node_id, w.node_path, w.relation_path, w.hops,
                   n.node_key, n.node_type
            FROM walk w JOIN graph_nodes n ON n.id=w.node_id
            WHERE w.hops > 0
              AND (%s IS NULL OR n.node_key=%s)
              AND (%s IS NULL OR n.node_type=%s)
            ORDER BY w.hops, n.node_key
            LIMIT 50
        """, (*params, target, target, target_type, target_type))
        walks = cur.fetchall()
        paths = []
        for final_id, node_path, relation_path, hops, final_key, final_type in walks:
            cur.execute("""
                SELECT id, node_key, node_type, label, document_type, source_url,
                       valid_from::text, valid_to::text
                FROM graph_nodes
                WHERE id = ANY(%s)
                ORDER BY array_position(%s, id)
            """, (node_path, node_path))
            node_rows = cur.fetchall()
            cur.execute("""
                SELECT e.relation_type, e.evidence, e.source_url,
                       e.valid_from::text, e.valid_to::text
                FROM generate_series(1, %s) AS step(i)
                JOIN graph_edges e
                  ON e.from_node_id=(%s)[step.i] AND e.to_node_id=(%s)[step.i+1]
                 AND e.relation_type=(%s)[step.i]
                ORDER BY step.i
            """, (len(node_path) - 1, node_path, node_path, relation_path))
            edge_rows = cur.fetchall()
            paths.append({
                "hops": hops,
                "target": {"node_key": final_key, "node_type": final_type},
                "nodes": [dict(zip(["id", "node_key", "node_type", "label", "document_type", "source_url", "valid_from", "valid_to"], row)) for row in node_rows],
                "edges": [dict(zip(["relation_type", "evidence", "source_url", "valid_from", "valid_to"], row)) for row in edge_rows[:hops]],
            })
        return JSONResponse({"start": start, "target": target, "target_type": target_type, "as_of": as_of, "paths": paths})
    finally:
        cur.close()
        conn.close()


@app.get("/api/graph/conflicts")
async def graph_conflicts(
    as_of: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
):
    """Return conservative conflict candidates from typed override/variation edges."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        params = []
        validity = ""
        if as_of:
            validity = " AND (e.valid_from IS NULL OR e.valid_from <= %s::date) AND (e.valid_to IS NULL OR e.valid_to >= %s::date)"
            params.extend([as_of, as_of])
        cur.execute(f"""
            SELECT e.id, e.relation_type, src.node_key, src.label,
                   dst.node_key, dst.label, e.evidence, e.source_url,
                   e.valid_from::text, e.valid_to::text, e.confidence
            FROM graph_edges e
            JOIN graph_nodes src ON src.id=e.from_node_id
            JOIN graph_nodes dst ON dst.id=e.to_node_id
            WHERE e.relation_type IN ('overrides','varies') {validity}
            ORDER BY e.relation_type, e.id
            LIMIT %s
        """, (*params, limit))
        columns = ["edge_id", "relation_type", "from_node", "from_label",
                   "to_node", "to_label", "evidence", "source_url",
                   "valid_from", "valid_to", "confidence"]
        candidates = [dict(zip(columns, row)) for row in cur.fetchall()]
        for candidate in candidates:
            if candidate["confidence"] is not None:
                candidate["confidence"] = float(candidate["confidence"])
        return JSONResponse({"status": "candidate_only", "conflicts": candidates, "count": len(candidates)})
    finally:
        cur.close()
        conn.close()


@app.get("/api/graph/timeline")
async def graph_timeline(node: str):
    """Return point-in-time versions or validity interval for one graph node."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, node_key, node_type, label, document_type, source_url,
                   valid_from::text, valid_to::text
            FROM graph_nodes WHERE node_key=%s
        """, (node,))
        row = cur.fetchone()
        if not row:
            return JSONResponse({"error": "Graph node not found"}, status_code=404)
        node_data = dict(zip(
            ["id", "node_key", "node_type", "label", "document_type", "source_url", "valid_from", "valid_to"],
            row,
        ))
        timeline = []
        if node.startswith("act:"):
            title_id = node[4:]
            cur.execute("""
                SELECT c.document_id, c.compilation_dt::text, c.is_latest, c.xml_path
                FROM compilations c JOIN acts a ON a.id=c.act_id
                WHERE a.title_id=%s ORDER BY c.compilation_dt
            """, (title_id,))
            timeline = [dict(zip(["document_id", "compilation_dt", "is_latest", "xml_path"], item)) for item in cur.fetchall()]
        else:
            timeline = [{
                "valid_from": node_data["valid_from"],
                "valid_to": node_data["valid_to"],
                "source_url": node_data["source_url"],
            }]
        return JSONResponse({"node": node_data, "timeline": timeline})
    finally:
        cur.close()
        conn.close()

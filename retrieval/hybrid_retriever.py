from __future__ import annotations

"""
Hybrid retrieval: dense (BGE-M3) + sparse (BGE-M3 lexical weights via pg full-text).
Fused with Reciprocal Rank Fusion (RRF).
"""
import json
import re
import psycopg2
from pgvector.psycopg2 import register_vector
from retrieval.dense_retriever import encode_query, get_model
from config import config

QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


def encode_query_full(query: str) -> tuple[list[float], dict[str, float]]:
    model = get_model()
    out = model.encode(
        [QUERY_PREFIX + query],
        return_dense=True,
        return_sparse=True,
    )
    dense = out["dense_vecs"][0].tolist()
    sparse = {str(k): float(v) for k, v in out["lexical_weights"][0].items()}
    return dense, sparse


def rrf_score(rank: int, k: int = None) -> float:
    k = k or config.rrf_k
    return 1.0 / (k + rank)


def hybrid_search(
    query: str,
    conn,
    k: int = None,
    alpha: float = None,
    act_id: int | None = None,
) -> list[dict]:
    if not config.enable_local_embeddings:
        return lexical_search(query, conn, k=k, act_id=act_id)

    k = k or config.top_k_retrieve
    alpha = alpha if alpha is not None else config.hybrid_alpha

    register_vector(conn)
    cur = conn.cursor()

    dense_vec, sparse_weights = encode_query_full(query)

    # ── Dense pass ───────────────────────────────────────────────────────────
    act_filter = "AND s.act_id = %s" if act_id else ""
    dense_params = [dense_vec, dense_vec] + ([act_id] if act_id else []) + [k * 2]

    cur.execute(f"""
        SELECT s.id, s.section_no, s.section_heading, s.body,
               a.name AS act_name, a.document_type, a.authority_level,
               c.compilation_dt::text, s.source_url,
               ROW_NUMBER() OVER (ORDER BY s.embedding <=> %s) AS rn
        FROM sections s
        JOIN acts a ON a.id = s.act_id
        JOIN compilations c ON c.id = s.compilation_id
        WHERE c.is_latest = true {act_filter}
        ORDER BY s.embedding <=> %s
        LIMIT %s
    """, dense_params)
    dense_rows = cur.fetchall()
    cols = ["id","section_no","section_heading","body","act_name",
            "document_type","authority_level","compilation_dt","source_url","rn"]
    dense_results = {r[0]: dict(zip(cols, r)) for r in dense_rows}

    # ── Keyword pass (pg full-text) ──────────────────────────────────────────
    # Build tsquery from top sparse tokens
    top_tokens = sorted(sparse_weights.items(), key=lambda x: -x[1])[:10]
    # Reconstruct terms from tokenizer vocabulary
    model = get_model()
    token_texts = [model.tokenizer.convert_ids_to_tokens([int(tid)])[0]
                   for tid, _ in top_tokens if tid.isdigit()]
    token_texts = [t for t in token_texts if t and not t.startswith("##") and len(t) > 2]

    keyword_results = {}
    if token_texts:
        tsq = " | ".join(token_texts[:8])
        kw_params = [tsq, tsq] + ([act_id] if act_id else []) + [k * 2]
        try:
            cur.execute(f"""
                SELECT s.id, s.section_no, s.section_heading, s.body,
                       a.name AS act_name, c.compilation_dt::text, s.source_url,
                       ROW_NUMBER() OVER (ORDER BY ts_rank(s.body_tsv, to_tsquery('english', %s)) DESC) AS rn
                FROM sections s
                JOIN acts a ON a.id = s.act_id
                JOIN compilations c ON c.id = s.compilation_id
                WHERE s.body_tsv @@ to_tsquery('english', %s)
                  AND c.is_latest = true {act_filter}
                ORDER BY ts_rank(s.body_tsv, to_tsquery('english', %s::text)) DESC
                LIMIT %s
            """, kw_params + [tsq])
            kw_rows = cur.fetchall()
            keyword_results = {r[0]: dict(zip(cols, r)) for r in kw_rows}
        except Exception:
            pass  # tsquery may fail on unusual tokens; fall back to dense only

    # ── RRF fusion ───────────────────────────────────────────────────────────
    all_ids = set(dense_results) | set(keyword_results)
    fused = {}
    for sid in all_ids:
        d_rank = dense_results[sid]["rn"] if sid in dense_results else k * 10
        k_rank = keyword_results[sid]["rn"] if sid in keyword_results else k * 10
        score = alpha * rrf_score(d_rank) + (1 - alpha) * rrf_score(k_rank)
        doc = (dense_results.get(sid) or keyword_results.get(sid)).copy()
        doc["score"] = score
        fused[sid] = doc

    ranked = sorted(fused.values(), key=lambda x: -x["score"])[:k]
    cur.close()
    return ranked


def lexical_search(query: str, conn, k: int = None, act_id: int | None = None) -> list[dict]:
    """Safe low-footprint fallback when BGE-M3 is not enabled locally."""
    k = k or config.top_k_retrieve
    cur = conn.cursor()
    # If a question contains the meaningful words of a document title, scope
    # the lexical pass to that document. This prevents generic terms such as
    # "award" or "leave" from pulling an unrelated Award above the named one.
    query_terms = set(re.findall(r"[a-z0-9]+", query.lower()))
    stop_terms = {"what", "does", "the", "say", "about", "is", "are", "for", "and", "in", "of", "to", "a", "an", "how", "can", "under", "with", "on", "from"}
    domain_terms = {
        "act", "acts", "award", "awards", "clause", "clauses", "classification",
        "employee", "employees", "employer", "employers", "employment", "entitlement",
        "fair", "guidance", "guide", "hours", "leave", "modern", "overtime", "pay",
        "penalty", "rate", "rates", "regulation", "regulations", "section", "wage",
        "wages", "work", "worker", "workers", "working", "agreement", "agreements",
        "national", "dismissal", "allowance", "allowances", "standard", "standards",
    }
    if not query_terms.intersection(domain_terms) and not re.search(r"\b(?:s|sec|section|clause|regulation)\s*\d", query.lower()):
        return []
    search_terms = [term for term in sorted(query_terms)
                    if term not in stop_terms and len(term) > 2]
    search_query = " | ".join(search_terms) or query
    section_match = re.search(r"\b(?:s|sec|section|clause|regulation)\s+(\d+[A-Za-z]?(?:\.\d+)*)", query.lower())
    exact_section = section_match.group(1) if section_match else "__no_exact_section__"
    cur.execute("SELECT id, name, document_type FROM acts")
    title_matches = []
    for candidate_id, name, document_type in cur.fetchall():
        title_terms = [t for t in re.findall(r"[a-z0-9]+", name.lower())
                       if t not in stop_terms and not t.isdigit()
                       and not re.fullmatch(r"ma\d+", t) and len(t) > 2]
        overlap = set(title_terms).intersection(query_terms)
        # Decision titles include the full case caption and citation. A user
        # normally names only the leading parties, so require a strong partial
        # match for decisions instead of requiring every caption token.
        decision_match = document_type == "decision" and len(overlap) >= 2
        full_title_match = len(title_terms) >= 2 and all(term in query_terms for term in title_terms)
        if full_title_match or decision_match:
            title_matches.append(candidate_id)

    if act_id:
        act_filter = "AND s.act_id = %s"
        scope_param = act_id
    elif title_matches:
        act_filter = "AND s.act_id = ANY(%s)"
        scope_param = title_matches
    else:
        act_filter = ""
        scope_param = None
    # Boost a document-title match so a question mentioning an Act or Award
    # does not get drowned out by generic words such as "award" or "leave".
    params = [exact_section, search_query, search_query, search_query, search_query,
              search_query, search_query,
              f"%{query}%", exact_section, f"%{query}%"]
    if scope_param is not None:
        params.append(scope_param)
    params.append(k)
    cur.execute(f"""
        SELECT s.id, s.section_no, s.section_heading, s.body,
               a.name AS act_name, a.document_type, a.authority_level,
               c.compilation_dt::text, s.source_url,
               greatest(
                   CASE WHEN s.section_no = %s THEN 100.0 ELSE 0 END,
                   ts_rank_cd(s.body_tsv, to_tsquery('english', %s)),
                   2.0 * ts_rank_cd(to_tsvector('english', a.name), to_tsquery('english', %s)),
                   1.25 * ts_rank_cd(to_tsvector('english', coalesce(s.section_heading, '')), to_tsquery('english', %s)),
                   0.01
               ) AS score
        FROM sections s
        JOIN acts a ON a.id = s.act_id
        JOIN compilations c ON c.id = s.compilation_id
        WHERE c.is_latest = true
          AND (s.body_tsv @@ to_tsquery('english', %s)
               OR to_tsvector('english', a.name) @@ to_tsquery('english', %s)
               OR to_tsvector('english', coalesce(s.section_heading, '')) @@ to_tsquery('english', %s)
               OR s.section_no ILIKE %s
               OR s.section_no = %s
               OR coalesce(s.section_heading, '') ILIKE %s)
          {act_filter}
        ORDER BY score DESC, s.id
        LIMIT %s
    """, params)
    rows = cur.fetchall()
    cur.close()
    cols = ["id", "section_no", "section_heading", "body", "act_name",
            "document_type", "authority_level", "compilation_dt", "source_url", "score"]
    return [dict(zip(cols, row)) for row in rows]

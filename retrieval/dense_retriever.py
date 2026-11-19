from __future__ import annotations

"""
Dense vector retrieval using BGE-M3 embeddings + pgvector HNSW.
"""
import psycopg2
from pgvector.psycopg2 import register_vector
from typing import Any, Optional
from config import config

_model: Optional[Any] = None

QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


def get_model() -> Any:
    global _model
    if _model is None:
        # Keep offline/full-text mode free of heavyweight model imports.
        from FlagEmbedding import BGEM3FlagModel
        _model = BGEM3FlagModel(config.embedding_model, use_fp16=True)
    return _model


def encode_query(query: str) -> list[float]:
    model = get_model()
    out = model.encode(
        [QUERY_PREFIX + query],
        return_dense=True,
        return_sparse=False,
    )
    return out["dense_vecs"][0].tolist()


def dense_search(
    query: str,
    conn,
    k: int = 20,
    act_id: int | None = None,
    compilation_dt: str | None = None,
) -> list[dict]:
    register_vector(conn)
    cur = conn.cursor()
    q_vec = encode_query(query)

    filters = []
    params: list = [q_vec, q_vec]

    if act_id is not None:
        filters.append("s.act_id = %s")
        params.append(act_id)
    if compilation_dt is not None:
        filters.append("c.compilation_dt = %s")
        params.append(compilation_dt)

    where = "WHERE " + " AND ".join(filters) if filters else ""
    params.append(k)

    sql = f"""
        SELECT s.id, s.section_no, s.section_heading, s.body,
               a.name AS act_name, c.compilation_dt::text,
               s.source_url,
               1 - (s.embedding <=> %s) AS score
        FROM sections s
        JOIN acts a ON a.id = s.act_id
        JOIN compilations c ON c.id = s.compilation_id
        {where}
        ORDER BY s.embedding <=> %s
        LIMIT %s
    """
    cur.execute(sql, params)
    cols = ["id","section_no","section_heading","body","act_name",
            "compilation_dt","source_url","score"]
    results = [dict(zip(cols, row)) for row in cur.fetchall()]
    cur.close()
    return results

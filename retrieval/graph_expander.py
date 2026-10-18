"""Bounded Graph-RAG expansion for already-retrieved evidence sections."""
from __future__ import annotations

def expand_section_ids(section_ids: list[int], conn, max_hops: int = 2, limit: int = 8) -> dict[int, int]:
    """Return section IDs reachable through non-containment graph relations.

    The parent Act is seeded explicitly, while ``contains`` edges are excluded
    from traversal. This prevents one Act node from exploding into every
    section in a corpus while still allowing a path such as section → Act ←
    decision → Award → section.
    """
    if not section_ids:
        return {}
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT DISTINCT a.title_id, a.document_type
            FROM sections s JOIN acts a ON a.id=s.act_id
            WHERE s.id = ANY(%s)
        """, (section_ids,))
        act_keys = []
        source_keys = []
        for title_id, document_type in cur.fetchall():
            act_keys.append(f"act:{title_id}")
            if document_type == "enterprise_agreement" and title_id.startswith("AG-"):
                source_keys.append(f"agreement:{title_id[3:]}")
            if document_type == "decision" and title_id.startswith("DEC-"):
                source_keys.append(f"decision:{title_id[4:]}")
        seed_keys = [f"section:{section_id}" for section_id in section_ids] + act_keys + source_keys
        cur.execute("""
            WITH RECURSIVE walk AS (
                SELECT n.id, n.node_key, ARRAY[n.id]::bigint[] AS path, 0 AS hops
                FROM graph_nodes n WHERE n.node_key = ANY(%s)
                UNION ALL
                SELECT CASE WHEN e.from_node_id=w.id THEN e.to_node_id ELSE e.from_node_id END,
                       next_node.node_key, w.path || CASE WHEN e.from_node_id=w.id THEN e.to_node_id ELSE e.from_node_id END,
                       w.hops + 1
                FROM walk w
                JOIN graph_edges e ON (e.from_node_id=w.id OR e.to_node_id=w.id)
                JOIN graph_nodes next_node ON next_node.id = CASE
                    WHEN e.from_node_id=w.id THEN e.to_node_id ELSE e.from_node_id END
                WHERE w.hops < %s
                  AND e.relation_type <> 'contains'
                  AND NOT (next_node.id = ANY(w.path))
            )
            SELECT (n.metadata->>'section_id')::bigint AS section_id, MIN(w.hops) AS hops
            FROM walk w JOIN graph_nodes n ON n.id=w.id
            WHERE n.node_type='section' AND n.metadata ? 'section_id'
            GROUP BY n.id, n.metadata->>'section_id'
            ORDER BY hops, section_id
            LIMIT %s
        """, (seed_keys, max_hops, limit))
        return {row[0]: row[1] for row in cur.fetchall()}
    finally:
        cur.close()


def load_expanded_sections(section_ids: list[int], conn, max_hops: int = 2, limit: int = 8) -> list[dict]:
    """Load graph-expanded sections in retriever-compatible shape."""
    expanded = expand_section_ids(section_ids, conn, max_hops=max_hops, limit=limit)
    if not expanded:
        return []
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT s.id, s.section_no, s.section_heading, s.body,
                   a.name, a.document_type, a.authority_level, a.title_id,
                   c.compilation_dt::text, s.source_url
            FROM sections s
            JOIN acts a ON a.id=s.act_id
            JOIN compilations c ON c.id=s.compilation_id
            WHERE s.id = ANY(%s)
            ORDER BY array_position(%s, s.id)
        """, (list(expanded), list(expanded)))
        columns = ["id", "section_no", "section_heading", "body", "act_name",
                   "document_type", "authority_level", "title_id", "compilation_dt", "source_url"]
        rows = []
        for row in cur.fetchall():
            item = dict(zip(columns, row))
            item["graph_hops"] = expanded[item["id"]]
            item["score"] = 0.0
            rows.append(item)
        return rows
    finally:
        cur.close()

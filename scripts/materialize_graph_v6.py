"""Project V1-V5 source-specific relations into the V6 temporal graph.

The ingestion tables remain the source of truth. This rebuild is idempotent:
the projection is cleared and rebuilt in one transaction so traversal never
sees a half-updated graph.
"""
from __future__ import annotations

import psycopg2
from psycopg2.extras import Json

from config import config


RELATION_MAP = {
    "cross_ref": "cross_ref",
    "definition": "defines",
    "delegation": "delegates",
    "override": "overrides",
    "other": "cross_ref",
}


def node(cur, key: str, node_type: str, label: str, document_type: str | None,
         source_url: str | None, valid_from=None, valid_to=None, metadata=None) -> int:
    cur.execute(
        """
        INSERT INTO graph_nodes
            (node_key, node_type, label, document_type, source_url, valid_from, valid_to, metadata)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (node_key) DO UPDATE SET
            node_type=EXCLUDED.node_type, label=EXCLUDED.label,
            document_type=EXCLUDED.document_type, source_url=EXCLUDED.source_url,
            valid_from=EXCLUDED.valid_from, valid_to=EXCLUDED.valid_to,
            metadata=EXCLUDED.metadata
        RETURNING id
        """,
        (key, node_type, label, document_type, source_url, valid_from, valid_to, Json(metadata or {})),
    )
    return cur.fetchone()[0]


def edge(cur, source: int, target: int, relation: str, evidence: str | None,
         source_url: str | None, valid_from=None, valid_to=None, confidence=1.0,
         metadata=None) -> None:
    cur.execute(
        """
        INSERT INTO graph_edges
            (from_node_id, to_node_id, relation_type, evidence, source_url,
             valid_from, valid_to, confidence, metadata)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (from_node_id, to_node_id, relation_type, evidence) DO NOTHING
        """,
        (source, target, relation, evidence, source_url, valid_from, valid_to,
         confidence, Json(metadata or {})),
    )


def main() -> None:
    conn = psycopg2.connect(config.db_url)
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM graph_edges")
        cur.execute("DELETE FROM graph_nodes")
        act_nodes: dict[int, int] = {}
        section_nodes: dict[int, int] = {}
        decision_nodes: dict[int, int] = {}
        agreement_nodes: dict[int, int] = {}

        cur.execute("""
            SELECT a.id, a.title_id, a.name, a.document_type, a.source_url,
                   MIN(c.compilation_dt), MAX(c.compilation_dt)
            FROM acts a LEFT JOIN compilations c ON c.act_id=a.id
            GROUP BY a.id ORDER BY a.id
        """)
        for act_id, title_id, name, doc_type, source_url, first_dt, last_dt in cur.fetchall():
            act_nodes[act_id] = node(
                cur, f"act:{title_id}", "act", name, doc_type, source_url,
                first_dt, last_dt, {"act_id": act_id, "title_id": title_id},
            )

        cur.execute("""
            WITH versions AS (
                SELECT act_id, compilation_dt,
                       LEAD(compilation_dt) OVER (PARTITION BY act_id ORDER BY compilation_dt) AS next_dt
                FROM (SELECT DISTINCT act_id, compilation_dt FROM compilations) v
            )
            SELECT s.id, s.act_id, s.section_no, s.section_heading, s.source_url,
                   a.name, a.document_type, c.compilation_dt,
                   CASE WHEN v.next_dt IS NULL THEN NULL ELSE v.next_dt - 1 END
            FROM sections s
            JOIN acts a ON a.id=s.act_id
            JOIN compilations c ON c.id=s.compilation_id
            JOIN versions v ON v.act_id=c.act_id AND v.compilation_dt=c.compilation_dt
            ORDER BY s.id
        """)
        for section_id, act_id, section_no, heading, source_url, act_name, doc_type, start, end in cur.fetchall():
            section_nodes[section_id] = node(
                cur, f"section:{section_id}", "section",
                f"{act_name} s {section_no}" + (f" — {heading}" if heading else ""),
                doc_type, source_url, start, end,
                {"section_id": section_id, "act_id": act_id, "section_no": section_no},
            )
            if act_id in act_nodes:
                edge(cur, act_nodes[act_id], section_nodes[section_id], "contains",
                     section_no, source_url, start, end)

        cur.execute("""
            SELECT d.id, d.decision_id, d.case_name, d.citation, d.source_url,
                   d.decision_date
            FROM decisions d ORDER BY d.id
        """)
        for decision_id, key, case_name, citation, source_url, decision_date in cur.fetchall():
            decision_nodes[decision_id] = node(
                cur, f"decision:{key}", "decision", f"{case_name} — {citation}",
                "decision", source_url, decision_date, None,
                {"decision_id": key, "citation": citation},
            )

        cur.execute("""
            SELECT ea.id, ea.agreement_id, a.name, ea.industry, ea.source_url,
                   ea.approval_date, ea.nominal_expiry
            FROM enterprise_agreements ea JOIN acts a ON a.id=ea.act_id
            ORDER BY ea.id
        """)
        for agreement_id, key, name, industry, source_url, start, end in cur.fetchall():
            agreement_nodes[agreement_id] = node(
                cur, f"agreement:{key}", "agreement", name,
                "enterprise_agreement", source_url, start, end,
                {"agreement_id": key, "industry": industry},
            )

        cur.execute("""
            SELECT r.from_section_id, r.to_section_id, r.ref_type, r.ref_text,
                   s.source_url, c.compilation_dt
            FROM section_refs r
            JOIN sections s ON s.id=r.from_section_id
            JOIN compilations c ON c.id=s.compilation_id
            WHERE r.to_section_id IS NOT NULL
        """)
        for source_id, target_id, ref_type, evidence, source_url, start in cur.fetchall():
            if source_id in section_nodes and target_id in section_nodes:
                edge(cur, section_nodes[source_id], section_nodes[target_id],
                     RELATION_MAP.get(ref_type, "cross_ref"), evidence, source_url, start)

        cur.execute("""
            SELECT dr.decision_id, dr.relation_type, dr.target_act_id, dr.target_award_id,
                   dr.target_section_no, dr.target_enterprise_agreement, dr.evidence,
                   d.source_url, d.decision_date
            FROM decision_refs dr JOIN decisions d ON d.id=dr.decision_id
        """)
        for source_id, relation, target_act, target_award, section_no, agreement_key, evidence, source_url, start in cur.fetchall():
            target = None
            if target_act or target_award:
                act_id = target_act or target_award
                if section_no:
                    cur.execute("SELECT id FROM sections WHERE act_id=%s AND section_no=%s ORDER BY id DESC LIMIT 1", (act_id, section_no))
                    row = cur.fetchone()
                    target = section_nodes.get(row[0]) if row else None
                target = target or act_nodes.get(act_id)
            if not target and agreement_key:
                cur.execute("SELECT id FROM enterprise_agreements WHERE agreement_id=%s", (agreement_key,))
                row = cur.fetchone()
                target = agreement_nodes.get(row[0]) if row else None
            if source_id in decision_nodes and target:
                edge(cur, decision_nodes[source_id], target, relation, evidence, source_url, start)

        cur.execute("""
            SELECT ar.agreement_id, ar.relation_type, ar.target_award_id,
                   ar.target_act_id, ar.target_decision_id, ar.target_clause,
                   ar.evidence, ea.source_url, ea.approval_date, ea.nominal_expiry
            FROM agreement_refs ar JOIN enterprise_agreements ea ON ea.id=ar.agreement_id
        """)
        for source_id, relation, target_award, target_act, target_decision, clause, evidence, source_url, start, end in cur.fetchall():
            target = act_nodes.get(target_award or target_act)
            if not target and target_decision:
                target = decision_nodes.get(target_decision)
            if source_id in agreement_nodes and target:
                edge(cur, agreement_nodes[source_id], target, relation, clause or evidence,
                     source_url, start, end)

        conn.commit()
        cur.execute("SELECT node_type, COUNT(*) FROM graph_nodes GROUP BY node_type ORDER BY node_type")
        nodes = dict(cur.fetchall())
        cur.execute("SELECT relation_type, COUNT(*) FROM graph_edges GROUP BY relation_type ORDER BY relation_type")
        edges = dict(cur.fetchall())
        print(f"V6 graph materialized: nodes={sum(nodes.values())} {nodes}; edges={sum(edges.values())} {edges}")
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()

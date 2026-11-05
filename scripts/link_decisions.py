from __future__ import annotations

"""Create V4 decision metadata and graph edges after text ingestion."""
import json
from pathlib import Path

import psycopg2

from config import config


def find_act(cur, title: str, document_type: str | None = None):
    if document_type:
        cur.execute(
            "SELECT id FROM acts WHERE lower(name) LIKE lower(%s) AND document_type=%s LIMIT 1",
            (f"%{title}%", document_type),
        )
    else:
        cur.execute("SELECT id FROM acts WHERE lower(name) LIKE lower(%s) LIMIT 1", (f"%{title}%",))
    row = cur.fetchone()
    return row[0] if row else None


def main() -> None:
    manifest = json.loads(Path("config/decisions_v4.json").read_text())
    conn = psycopg2.connect(config.db_url)
    cur = conn.cursor()
    linked = 0
    edges = 0
    for record in manifest:
        cur.execute("SELECT id FROM acts WHERE title_id=%s", (f"DEC-{record['id']}",))
        row = cur.fetchone()
        if not row:
            continue
        act_id = row[0]
        cur.execute(
            """
            INSERT INTO decisions
                (decision_id, act_id, case_name, citation, decision_date, category,
                 authority_level, source_url)
            VALUES (%s,%s,%s,%s,%s,%s,'decision',%s)
            ON CONFLICT (decision_id) DO UPDATE SET
                act_id=EXCLUDED.act_id, case_name=EXCLUDED.case_name,
                citation=EXCLUDED.citation, decision_date=EXCLUDED.decision_date,
                category=EXCLUDED.category, source_url=EXCLUDED.source_url
            RETURNING id
            """,
            (record["id"], act_id, record["case_name"], record["citation"],
             record["decision_date"], record["category"], record["url"]),
        )
        decision_id = cur.fetchone()[0]
        cur.execute("DELETE FROM decision_refs WHERE decision_id=%s", (decision_id,))
        linked += 1
        for relation in record.get("relations", []):
            relation_type = relation["type"]
            target_act_id = find_act(cur, relation.get("target_title", "")) if relation.get("target_title") else None
            target_award_id = find_act(cur, relation.get("target_award", ""), "award") if relation.get("target_award") else None
            sections = relation.get("sections") or [None]
            for section in sections:
                cur.execute(
                    """
                    INSERT INTO decision_refs
                        (decision_id, relation_type, target_act_id, target_section_no,
                         target_award_id, target_clause, target_enterprise_agreement, evidence)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (decision_id, relation_type, target_act_id, section,
                     target_award_id, relation.get("target_clause"),
                     relation.get("target_enterprise_agreement"), record["citation"]),
                )
                edges += 1
    conn.commit()
    cur.close()
    conn.close()
    print(f"Linked {linked} decisions and created {edges} graph edges")


if __name__ == "__main__":
    main()

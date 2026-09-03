"""Persist V5 agreement metadata and Award/decision graph edges."""
import json
from pathlib import Path

import psycopg2

from config import config


def find_award(cur, title: str):
    cur.execute(
        "SELECT id FROM acts WHERE document_type='award' AND lower(name) LIKE lower(%s) LIMIT 1",
        (f"%{title}%",),
    )
    row = cur.fetchone()
    return row[0] if row else None


def find_decision(cur, citation: str):
    cur.execute("SELECT id FROM decisions WHERE citation=%s LIMIT 1", (citation,))
    row = cur.fetchone()
    return row[0] if row else None


def main() -> None:
    records = json.loads(Path("config/agreements_v5.json").read_text())
    conn = psycopg2.connect(config.db_url)
    cur = conn.cursor()
    linked = 0
    edges = 0
    for record in records:
        cur.execute("SELECT id FROM acts WHERE title_id=%s", (f"AG-{record['agreement_id']}",))
        row = cur.fetchone()
        if not row:
            continue
        act_id = row[0]
        cur.execute(
            """
            INSERT INTO enterprise_agreements
                (act_id, agreement_id, matter_number, version, employer, industry,
                 approval_date, nominal_expiry, status, source_url, metadata_source_url)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (agreement_id) DO UPDATE SET
                act_id=EXCLUDED.act_id, matter_number=EXCLUDED.matter_number,
                version=EXCLUDED.version, employer=EXCLUDED.employer,
                industry=EXCLUDED.industry, approval_date=EXCLUDED.approval_date,
                nominal_expiry=EXCLUDED.nominal_expiry, status=EXCLUDED.status,
                source_url=EXCLUDED.source_url,
                metadata_source_url=EXCLUDED.metadata_source_url
            RETURNING id
            """,
            (
                act_id, record["agreement_id"], record.get("matter_number"),
                record.get("version"), record.get("employer"), record.get("industry"),
                record.get("approval_date"), record.get("nominal_expiry"),
                record.get("status", "published"), record["url"],
                "https://www.fwc.gov.au/work-conditions/enterprise-agreements/find-enterprise-agreement",
            ),
        )
        agreement_id = cur.fetchone()[0]
        cur.execute("DELETE FROM agreement_refs WHERE agreement_id=%s", (agreement_id,))
        linked += 1
        for relation in record.get("award_links", []):
            award_id = find_award(cur, relation["award"])
            cur.execute(
                """
                INSERT INTO agreement_refs
                    (agreement_id, relation_type, target_award_id, target_clause, evidence)
                VALUES (%s,%s,%s,%s,%s)
                """,
                (agreement_id, relation.get("relation", "compares_to"), award_id,
                 relation.get("clause"), record["agreement_id"]),
            )
            edges += 1
        if record.get("approval_decision_citation"):
            decision_id = find_decision(cur, record["approval_decision_citation"])
            cur.execute(
                """
                INSERT INTO agreement_refs
                    (agreement_id, relation_type, target_decision_id, evidence)
                VALUES (%s,'approved_by',%s,%s)
                """,
                (agreement_id, decision_id, record["approval_decision_citation"]),
            )
            edges += 1
    conn.commit()
    cur.close()
    conn.close()
    print(f"Linked {linked} enterprise agreements and created {edges} graph edges")


if __name__ == "__main__":
    main()

"""Check the deterministic V5 corpus counts used by release acceptance.

This is intentionally an invariant check rather than a benchmark.  It catches
partial ingestion (for example, a missing agreement PDF or stale chunks) before
the measured retrieval numbers are used in release notes or a resume.
"""
import psycopg2

from config import config


EXPECTED = {
    "agreements": 6,
    "agreement_chunks": 241,
    "decisions": 7,
    "decision_chunks": 246,
    "compares_to_edges": 6,
    "approved_by_edges": 1,
    "embeddings": 0,
}


def main() -> None:
    conn = psycopg2.connect(config.db_url)
    cur = conn.cursor()
    queries = {
        "agreements": "SELECT COUNT(*) FROM enterprise_agreements",
        "agreement_chunks": """
            SELECT COUNT(*) FROM sections s JOIN acts a ON a.id=s.act_id
            WHERE a.document_type='enterprise_agreement'
        """,
        "decisions": "SELECT COUNT(*) FROM decisions",
        "decision_chunks": """
            SELECT COUNT(*) FROM sections s JOIN acts a ON a.id=s.act_id
            WHERE a.document_type='decision'
        """,
        "compares_to_edges": "SELECT COUNT(*) FROM agreement_refs WHERE relation_type='compares_to'",
        "approved_by_edges": "SELECT COUNT(*) FROM agreement_refs WHERE relation_type='approved_by'",
        "embeddings": "SELECT COUNT(*) FROM sections WHERE embedding IS NOT NULL",
    }
    actual = {}
    try:
        for name, query in queries.items():
            cur.execute(query)
            actual[name] = cur.fetchone()[0]
    finally:
        cur.close()
        conn.close()
    assert actual == EXPECTED, f"V5 count drift: expected={EXPECTED}, actual={actual}"
    print("V5 corpus counts passed:", ", ".join(f"{key}={value}" for key, value in actual.items()))


if __name__ == "__main__":
    main()

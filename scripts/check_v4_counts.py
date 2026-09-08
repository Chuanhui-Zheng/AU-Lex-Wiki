"""Verify the expected local V4 corpus shape after ingestion."""
import psycopg2

from config import config


EXPECTED_DOCUMENTS = {
    "award": 122,
    "decision": 6,
    "guidance": 30,
    "legislation": 2,
    "pay_guide": 121,
}


def main() -> None:
    conn = psycopg2.connect(config.db_url)
    cur = conn.cursor()
    cur.execute("SELECT document_type, COUNT(*) FROM acts GROUP BY document_type")
    counts = dict(cur.fetchall())
    cur.execute("SELECT COUNT(*) FROM sections")
    sections = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM decisions")
    decisions = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM sections WHERE embedding IS NOT NULL OR sparse_weights IS NOT NULL")
    vectors = cur.fetchone()[0]
    cur.close()
    conn.close()
    for document_type, expected in EXPECTED_DOCUMENTS.items():
        assert counts.get(document_type) == expected, (document_type, counts.get(document_type), expected)
    assert sections >= 16619, f"unexpected section count: {sections}"
    assert decisions >= 6, f"unexpected decision count: {decisions}"
    assert vectors == 0, f"text-only profile contains {vectors} vector rows"
    print(f"V4 counts passed: documents={counts}, sections={sections}, vectors={vectors}")


if __name__ == "__main__":
    main()

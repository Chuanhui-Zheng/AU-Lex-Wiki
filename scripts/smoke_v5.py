"""Acceptance smoke test for V5 Enterprise Agreement retrieval and graph links."""
import psycopg2

from config import config
from pipeline.rag_pipeline import answer


def main() -> None:
    conn = psycopg2.connect(config.db_url)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM enterprise_agreements")
    agreements = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM agreement_refs WHERE relation_type='compares_to'")
    award_edges = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM agreement_refs WHERE relation_type='approved_by'")
    approval_edges = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM sections WHERE embedding IS NOT NULL OR sparse_weights IS NOT NULL")
    vectors = cur.fetchone()[0]
    cur.close()
    conn.close()
    assert agreements == 6
    assert award_edges == 6
    assert approval_edges >= 1
    assert vectors == 0
    result = answer(
        "What does the Apple Australia National Enterprise Agreement say about Sunday pay?",
        mode="offline",
    )
    assert not result["refused"] and result["sources"]
    assert any(source.get("agreement_id") == "AE521821" for source in result["sources"])
    refused = answer("What is the moon made of?", mode="offline")
    assert refused["refused"]
    print(f"V5 smoke passed: agreements={agreements}, award_edges={award_edges}, approval_edges={approval_edges}, vectors={vectors}")


if __name__ == "__main__":
    main()

"""Acceptance smoke test for the curated V4 FWC decision layer."""
import psycopg2

from config import config
from pipeline.rag_pipeline import answer


def main() -> None:
    conn = psycopg2.connect(config.db_url)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM decisions")
    decisions = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM decision_refs")
    edges = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM sections WHERE embedding IS NOT NULL OR sparse_weights IS NOT NULL")
    vectors = cur.fetchone()[0]
    cur.close()
    conn.close()
    assert decisions >= 6, "The curated FWC decision set is incomplete"
    assert edges >= decisions, "Decision graph edges were not linked"
    assert vectors == 0, "The default profile must remain text-only"
    result = answer(
        "What did the Fair Work Commission decide in Gold Tiger Logistics about unfair dismissal?",
        mode="offline",
    )
    assert not result["refused"] and result["sources"], "Decision retrieval returned no evidence"
    assert any(source["document_type"] == "decision" for source in result["sources"])
    refused = answer("What is the moon made of?", mode="offline")
    assert refused["refused"], "Out-of-scope questions must be refused"
    print(f"V4 smoke passed: decisions={decisions}, graph_edges={edges}, vectors={vectors}")


if __name__ == "__main__":
    main()

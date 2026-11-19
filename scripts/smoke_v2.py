"""Small local acceptance smoke test for the text-only V2 profile."""
import psycopg2

from config import config
from pipeline.rag_pipeline import answer


def main() -> None:
    conn = psycopg2.connect(config.db_url)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM acts WHERE document_type='award'")
    awards = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM acts WHERE document_type='pay_guide'")
    guides = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM sections WHERE embedding IS NOT NULL OR sparse_weights IS NOT NULL")
    vectors = cur.fetchone()[0]
    cur.close()
    conn.close()

    assert awards > 0, "No Modern Awards are indexed"
    assert guides > 0, "No Pay Guides are indexed"
    assert vectors == 0, "The text-only profile contains vectors"

    grounded = answer("What is the minimum hourly rate in the Restaurant Industry Award?", mode="offline")
    refused = answer("What is the moon made of?", mode="offline")
    assert not grounded["refused"] and grounded["sources"]
    assert refused["refused"]
    print(f"V2 smoke passed: awards={awards}, pay_guides={guides}, vectors={vectors}")


if __name__ == "__main__":
    main()

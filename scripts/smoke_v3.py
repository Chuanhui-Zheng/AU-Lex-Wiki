"""Local acceptance smoke test for the V3 official-guidance profile."""
import psycopg2

from config import config
from pipeline.rag_pipeline import answer


def main() -> None:
    conn = psycopg2.connect(config.db_url)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM acts WHERE document_type='guidance' AND authority_level='official_guidance'")
    guidance = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM sections WHERE embedding IS NOT NULL OR sparse_weights IS NOT NULL")
    vectors = cur.fetchone()[0]
    cur.close()
    conn.close()
    assert guidance > 0, "No official FWO guidance is indexed"
    assert vectors == 0, "The text-only profile contains vectors"
    grounded = answer("What does the Your guide to casual employment say about casual employment?", mode="offline")
    refused = answer("What is the moon made of?", mode="offline")
    assert not grounded["refused"] and grounded["sources"]
    assert all(source["authority_level"] == "official_guidance" for source in grounded["sources"])
    assert refused["refused"]
    print(f"V3 smoke passed: guidance={guidance}, vectors={vectors}")


if __name__ == "__main__":
    main()

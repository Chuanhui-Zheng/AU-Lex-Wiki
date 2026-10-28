"""Check cross-Act reference resolution and projection coverage."""
import psycopg2

from config import config


def main() -> None:
    conn = psycopg2.connect(config.db_url)
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT COUNT(*) FILTER (WHERE to_section_id IS NOT NULL),
                   COUNT(*) FILTER (WHERE to_section_id IS NULL AND to_act_name IS NOT NULL)
            FROM section_refs
        """)
        resolved, unresolved = cur.fetchone()
        cur.execute("SELECT COUNT(*) FROM graph_edges WHERE relation_type='cross_ref'")
        projected = cur.fetchone()[0]
    finally:
        cur.close()
        conn.close()
    assert resolved > 0
    assert projected > 0
    print(f"V6 cross-Act check passed: resolved={resolved}, unresolved={unresolved}, projected_cross_ref_edges={projected}")


if __name__ == "__main__":
    main()

"""Resolve cross-Act section references against the latest indexed versions."""
import psycopg2

from config import config


def main() -> None:
    conn = psycopg2.connect(config.db_url)
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE section_refs r
            SET to_section_id=s.id
            FROM sections s
            JOIN acts a ON a.id=s.act_id
            JOIN compilations c ON c.id=s.compilation_id
            WHERE r.to_section_id IS NULL
              AND r.to_act_name IS NOT NULL
              AND c.is_latest=true
              AND lower(trim(a.name))=lower(trim(r.to_act_name))
              AND s.section_no=r.to_section_no
        """)
        resolved = cur.rowcount
        cur.execute("""
            SELECT COUNT(*) FROM section_refs
            WHERE to_section_id IS NULL AND to_act_name IS NOT NULL
        """)
        remaining = cur.fetchone()[0]
        conn.commit()
        print(f"V6 cross-Act resolution passed: resolved={resolved}, remaining={remaining}")
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()

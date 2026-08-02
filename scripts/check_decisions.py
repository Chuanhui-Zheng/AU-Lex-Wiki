"""Print concise provenance and graph counts for the V4 decision collection."""
import psycopg2

from config import config


def main() -> None:
    conn = psycopg2.connect(config.db_url)
    cur = conn.cursor()
    cur.execute("""
        SELECT d.category, COUNT(*), MIN(d.decision_date), MAX(d.decision_date)
        FROM decisions d GROUP BY d.category ORDER BY d.category
    """)
    for category, count, first_date, last_date in cur.fetchall():
        print(f"{category}: {count} decisions ({first_date} to {last_date})")
    cur.execute("""
        SELECT relation_type, COUNT(*) FROM decision_refs
        GROUP BY relation_type ORDER BY relation_type
    """)
    print("Graph edges:")
    for relation_type, count in cur.fetchall():
        print(f"  {relation_type}: {count}")
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()

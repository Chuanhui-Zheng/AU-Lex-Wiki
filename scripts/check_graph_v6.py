"""Verify V6 graph projection integrity and temporal edge metadata."""
import psycopg2

from config import config


def main() -> None:
    conn = psycopg2.connect(config.db_url)
    cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM graph_nodes")
        nodes = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM graph_edges")
        edges = cur.fetchone()[0]
        cur.execute("""
            SELECT COUNT(*) FROM graph_edges e
            LEFT JOIN graph_nodes n1 ON n1.id=e.from_node_id
            LEFT JOIN graph_nodes n2 ON n2.id=e.to_node_id
            WHERE n1.id IS NULL OR n2.id IS NULL
        """)
        dangling = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM graph_edges WHERE valid_from IS NOT NULL AND valid_to IS NOT NULL AND valid_from > valid_to")
        inverted = cur.fetchone()[0]
        cur.execute("""
            SELECT COUNT(*) FROM graph_edges
            WHERE relation_type IN ('cites','interprets','concerns','compares_to','approved_by')
              AND source_url IS NULL
        """)
        ungrounded_edges = cur.fetchone()[0]
        cur.execute("""
            SELECT COUNT(*) FROM graph_edges
            WHERE relation_type IN ('cites','interprets','concerns','compares_to','approved_by')
              AND valid_from IS NOT NULL
        """)
        temporal_edges = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM graph_nodes WHERE valid_from IS NOT NULL")
        temporal_nodes = cur.fetchone()[0]
    finally:
        cur.close()
        conn.close()
    assert nodes > 0 and edges > 0
    assert dangling == 0, dangling
    assert inverted == 0, inverted
    assert ungrounded_edges == 0, ungrounded_edges
    assert temporal_edges > 0
    assert temporal_nodes > 0
    print(
        "V6 graph integrity passed: "
        f"nodes={nodes}, edges={edges}, temporal_nodes={temporal_nodes}, "
        f"temporal_edges={temporal_edges}, dangling={dangling}, inverted_intervals={inverted}"
    )


if __name__ == "__main__":
    main()

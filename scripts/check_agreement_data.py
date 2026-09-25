"""Check agreement chunk completeness and graph resolution after ingestion."""
import json
from pathlib import Path

import psycopg2

from config import config


def main() -> None:
    records = json.loads(Path("data/agreements_index.json").read_text())
    chunk_total = 0
    for record in records:
        path = Path(config.data_dir) / "chunks" / f"agreement_{record['agreement_id'].lower()}.jsonl"
        assert path.is_file(), record["agreement_id"]
        count = sum(1 for line in path.read_text().splitlines() if line.strip())
        assert count > 1, (record["agreement_id"], count)
        chunk_total += count
    conn = psycopg2.connect(config.db_url)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM acts WHERE document_type='enterprise_agreement'")
    acts = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM sections s JOIN acts a ON a.id=s.act_id WHERE a.document_type='enterprise_agreement'")
    sections = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM agreement_refs WHERE target_award_id IS NULL AND relation_type='compares_to'")
    unresolved = cur.fetchone()[0]
    cur.close()
    conn.close()
    assert acts == len(records) == 6
    assert sections == chunk_total
    assert unresolved == 0
    print(f"V5 agreement data passed: agreements={acts}, chunks={sections}, unresolved_award_edges={unresolved}")


if __name__ == "__main__":
    main()

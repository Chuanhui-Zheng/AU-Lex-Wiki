"""Evaluate direct versus bounded multi-hop coverage in the V6 graph."""
from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path

import psycopg2

from config import config


CASES = Path("config/eval_graph_v6.json")
REPORT = Path("docs/RAG_EVALUATION_V6.md")


def shortest_hops(cur, start: str, target: str, max_hops: int) -> int | None:
    cur.execute("""
        WITH RECURSIVE walk AS (
            SELECT n.id, ARRAY[n.id]::bigint[] AS path, 0 AS hops
            FROM graph_nodes n WHERE n.node_key=%s
            UNION ALL
            SELECT e.to_node_id, w.path || e.to_node_id, w.hops + 1
            FROM walk w JOIN graph_edges e ON e.from_node_id=w.id
            JOIN graph_nodes next_node ON next_node.id=e.to_node_id
            WHERE w.hops < %s AND NOT (e.to_node_id=ANY(w.path))
        )
        SELECT MIN(w.hops)
        FROM walk w JOIN graph_nodes n ON n.id=w.id
        WHERE n.node_key=%s AND w.hops > 0
    """, (start, max_hops, target))
    return cur.fetchone()[0]


def render(payload: dict) -> str:
    direct = payload["direct"]
    graph = payload["bounded_graph"]
    delta = graph["hit_rate"] - direct["hit_rate"]
    return f"""# V6 Graph-RAG evaluation

Generated: `{payload['generated_at']}`
Profile: unified PostgreSQL graph projection over Acts, sections, FWC decisions and Enterprise Agreements.

## Resume-ready comparison

| Metric | Direct one-hop baseline | Bounded Graph-RAG (≤3 hops) | Change |
|---|---:|---:|---:|
| Target path hit rate | {direct['hit_rate'] * 100:.1f}% | {graph['hit_rate'] * 100:.1f}% | {delta * 100:+.1f} pp |
| Successful cases | {direct['hits']}/{direct['total']} | {graph['hits']}/{graph['total']} | — |
| Median successful path length | {direct['median_hops']:.1f} | {graph['median_hops']:.1f} | {graph['median_hops'] - direct['median_hops']:+.1f} hops |

The fixed set contains {payload['cases']} source-linked paths. The baseline
only follows one edge; Graph-RAG follows a bounded directed path and records
the intermediate nodes. This is graph path coverage, not a claim of legal
correctness or generated-answer faithfulness.

## Cases

| Case | Direct hops | Bounded Graph-RAG hops |
|---|---:|---:|
""" + "\n".join(
        f"| {case['name']} | {case['direct_hops'] if case['direct_hops'] is not None else 'miss'} | {case['graph_hops'] if case['graph_hops'] is not None else 'miss'} |"
        for case in payload["results"]
    ) + """

## Reproduce

```bash
python -m scripts.evaluate_graph_v6 \\
  --cases config/eval_graph_v6.json \\
  --report docs/RAG_EVALUATION_V6.md
```
"""


def summary(results: list[dict], key: str) -> dict:
    hops = [item[key] for item in results if item[key] is not None]
    return {
        "hits": len(hops),
        "total": len(results),
        "hit_rate": len(hops) / len(results),
        "median_hops": statistics.median(hops) if hops else 0.0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=CASES)
    parser.add_argument("--report", type=Path, default=REPORT)
    args = parser.parse_args()
    cases = json.loads(args.cases.read_text())
    conn = psycopg2.connect(config.db_url)
    cur = conn.cursor()
    results = []
    started = time.perf_counter()
    for case in cases:
        results.append({
            **case,
            "direct_hops": shortest_hops(cur, case["start"], case["target"], 1),
            "graph_hops": shortest_hops(cur, case["start"], case["target"], case.get("max_hops", 3)),
        })
    conn.close()
    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cases": len(results),
        "direct": summary(results, "direct_hops"),
        "bounded_graph": summary(results, "graph_hops"),
        "elapsed_ms": (time.perf_counter() - started) * 1000,
        "results": results,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(render(payload))
    print(render(payload))


if __name__ == "__main__":
    main()

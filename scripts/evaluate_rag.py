"""Benchmark retrieval, evidence coverage, refusal and latency.

This evaluator is intentionally honest about the current text-only profile:
it reports retrieval metrics and an evidence-coverage proxy. RAGAS Faithfulness
and Answer Correctness require generated answers plus a judge model, so this
script does not invent those values when running offline.
"""
from __future__ import annotations

import json
import statistics
import time
from pathlib import Path

import psycopg2

from config import config
from pipeline.rag_pipeline import answer
from retrieval.hybrid_retriever import lexical_search


K = 5
QUESTIONS = Path("config/eval_questions_v2.json")
REPORT = Path("docs/RAG_EVALUATION.md")
JSON_REPORT = Path("output/rag_evaluation_v2.json")


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, round((len(ordered) - 1) * p))
    return ordered[index]


def baseline_search(query: str, conn, k: int = 20) -> list[dict]:
    """The pre-V2 simple PostgreSQL FTS baseline used for comparison."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT s.id, s.section_no, s.section_heading, s.body,
               a.name AS act_name, a.document_type, a.authority_level,
               c.compilation_dt::text, s.source_url,
               ts_rank_cd(s.body_tsv, plainto_tsquery('english', %s)) AS score
        FROM sections s
        JOIN acts a ON a.id = s.act_id
        JOIN compilations c ON c.id = s.compilation_id
        WHERE c.is_latest = true
          AND s.body_tsv @@ plainto_tsquery('english', %s)
        ORDER BY score DESC, s.id
        LIMIT %s
        """,
        (query, query, k),
    )
    rows = cur.fetchall()
    cur.close()
    columns = [
        "id", "section_no", "section_heading", "body", "act_name",
        "document_type", "authority_level", "compilation_dt", "source_url", "score",
    ]
    return [dict(zip(columns, row)) for row in rows]


def match_rank(rows: list[dict], item: dict) -> int | None:
    target = item["target_title"].lower()
    section = item.get("expected_section")
    for rank, row in enumerate(rows[:K], 1):
        title_match = target in row.get("act_name", "").lower()
        section_match = not section or row.get("section_no") == section
        if title_match and section_match:
            return rank
    return None


def evidence_coverage(rows: list[dict], item: dict) -> float:
    haystack = " ".join(
        f"{row.get('act_name', '')} {row.get('section_heading', '')} {row.get('body', '')}"
        for row in rows[:K]
    ).lower()
    terms = item.get("expected_terms", [])
    return sum(term.lower() in haystack for term in terms) / len(terms) if terms else 1.0


def retrieval_metrics(results: list[dict], label: str) -> dict:
    in_scope = [item for item in results if item["in_scope"]]
    ranks = [item[f"{label}_rank"] for item in in_scope if item[f"{label}_rank"]]
    return {
        "label": label,
        "questions": len(in_scope),
        "hit_rate_at_5": len(ranks) / len(in_scope),
        "mrr_at_5": sum(1 / rank for rank in ranks) / len(in_scope),
        "mean_evidence_coverage": statistics.mean(
            item[f"{label}_coverage"] for item in in_scope
        ),
    }


def render_report(payload: dict) -> str:
    baseline = payload["retrieval"]["baseline"]
    optimized = payload["retrieval"]["optimized"]
    hit_delta = optimized["hit_rate_at_5"] - baseline["hit_rate_at_5"]
    mrr_delta = optimized["mrr_at_5"] - baseline["mrr_at_5"]
    coverage_delta = optimized["mean_evidence_coverage"] - baseline["mean_evidence_coverage"]
    refusal = payload["refusal"]
    latency = payload["latency_ms"]
    return f"""# RAG evaluation report

Generated: `{payload['generated_at']}`  
Profile: PostgreSQL full-text, title-aware retrieval, no BGE-M3 vectors.

## Resume-ready comparison

| Metric | Baseline: simple PostgreSQL FTS | Optimized: title-aware + domain-gated FTS | Change |
|---|---:|---:|---:|
| Recall@5 / source hit rate | {pct(baseline['hit_rate_at_5'])} | {pct(optimized['hit_rate_at_5'])} | {hit_delta * 100:+.1f} pp |
| MRR@5 | {baseline['mrr_at_5']:.3f} | {optimized['mrr_at_5']:.3f} | {mrr_delta:+.3f} |
| Evidence-term coverage proxy | {pct(baseline['mean_evidence_coverage'])} | {pct(optimized['mean_evidence_coverage'])} | {coverage_delta * 100:+.1f} pp |

The comparison uses `{payload['questions']['in_scope']}` in-scope questions from
`config/eval_questions_v2.json`; each has one gold document title and optional
section/term checks. “Recall@5” is therefore source hit rate for this single-gold
benchmark, not a claim about all Australian workplace-law questions.

## Refusal and performance

| Metric | Result |
|---|---:|
| Refusal accuracy | {pct(refusal['accuracy'])} ({refusal['correct']}/{refusal['total']}) |
| Median retrieval latency | {latency['median']:.1f} ms |
| P95 retrieval latency | {latency['p95']:.1f} ms |

## What is and is not measured

- The offline run measures retrieval, evidence-term coverage, refusal accuracy
  and local latency.
- RAGAS Faithfulness and Answer Correctness are **not** claimed here because
  the default profile does not call an LLM judge. They should be measured in a
  separate online evaluation with a frozen model, prompt and judge set.
- The offline Ask answer is evidence-only and returns source markers; it does
  not silently fabricate a generated legal conclusion.

## Reproduce

```bash
python -m scripts.evaluate_rag
```
"""


def main() -> None:
    questions = json.loads(QUESTIONS.read_text())
    conn = psycopg2.connect(config.db_url)
    results = []
    optimized_latencies = []
    refusal_correct = 0
    for item in questions:
        started = time.perf_counter()
        baseline = baseline_search(item["question"], conn)
        baseline_ms = (time.perf_counter() - started) * 1000
        started = time.perf_counter()
        optimized = lexical_search(item["question"], conn, k=20)
        optimized_latencies.append((time.perf_counter() - started) * 1000)
        result = {
            **item,
            "baseline_rank": match_rank(baseline, item),
            "optimized_rank": match_rank(optimized, item),
            "baseline_coverage": evidence_coverage(baseline, item),
            "optimized_coverage": evidence_coverage(optimized, item),
            "baseline_latency_ms": baseline_ms,
        }
        outcome = answer(item["question"], conn=conn, mode="offline")
        expected_refusal = not item["in_scope"]
        if bool(outcome["refused"]) == expected_refusal:
            refusal_correct += 1
        result["refused"] = outcome["refused"]
        results.append(result)
    conn.close()

    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "profile": "postgres_fts_title_aware_text_only",
        "questions": {"total": len(questions), "in_scope": sum(q["in_scope"] for q in questions)},
        "retrieval": {
            "baseline": retrieval_metrics(results, "baseline"),
            "optimized": retrieval_metrics(results, "optimized"),
        },
        "refusal": {"correct": refusal_correct, "total": len(questions), "accuracy": refusal_correct / len(questions)},
        "latency_ms": {
            "median": statistics.median(optimized_latencies),
            "p95": percentile(optimized_latencies, 0.95),
        },
        "cases": results,
    }
    JSON_REPORT.parent.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(payload, indent=2))
    REPORT.write_text(render_report(payload))
    print(render_report(payload))


if __name__ == "__main__":
    main()

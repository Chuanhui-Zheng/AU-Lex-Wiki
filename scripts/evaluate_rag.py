"""Benchmark retrieval, evidence coverage, refusal and latency.

This evaluator is intentionally honest about the current text-only profile:
it reports retrieval metrics and an evidence-coverage proxy. RAGAS Faithfulness
and Answer Correctness require generated answers plus a judge model, so this
script does not invent those values when running offline.
"""
from __future__ import annotations

import json
import math
import random
import re
import statistics
import time
import argparse
from collections import Counter
from pathlib import Path

import psycopg2

from config import config
from pipeline.rag_pipeline import answer
from retrieval.hybrid_retriever import lexical_search


K = 10
REPORT_K = (1, 3, 5, 10)
QUESTIONS = Path("config/eval_questions_v5_large.json")
REPORT = Path("docs/RAG_EVALUATION_V5_LARGE.md")
JSON_REPORT = Path("output/rag_evaluation_v5_large.json")


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


def fair_title_search(query: str, conn, k: int = 20) -> list[dict]:
    """Fair ablation: title/body/heading FTS without boosting or scoping."""
    stop_terms = {"what", "does", "the", "say", "about", "is", "are", "for", "and", "in", "of", "to", "a", "an", "how", "can", "under", "with", "on", "from"}
    terms = [term for term in re.findall(r"[a-z0-9]+", query.lower()) if term not in stop_terms and len(term) > 2]
    tsquery = " | ".join(terms) or query
    cur = conn.cursor()
    cur.execute(
        """
        SELECT s.id, s.section_no, s.section_heading, s.body,
               a.name AS act_name, a.document_type, a.authority_level, a.title_id,
               c.compilation_dt::text, s.source_url,
               greatest(
                   ts_rank_cd(s.body_tsv, to_tsquery('english', %s)),
                   ts_rank_cd(to_tsvector('english', a.name), to_tsquery('english', %s)),
                   ts_rank_cd(to_tsvector('english', coalesce(s.section_heading, '')), to_tsquery('english', %s))
               ) AS score
        FROM sections s
        JOIN acts a ON a.id=s.act_id
        JOIN compilations c ON c.id=s.compilation_id
        WHERE c.is_latest = true
          AND (s.body_tsv @@ to_tsquery('english', %s)
               OR to_tsvector('english', a.name) @@ to_tsquery('english', %s)
               OR to_tsvector('english', coalesce(s.section_heading, '')) @@ to_tsquery('english', %s))
        ORDER BY score DESC, s.id
        LIMIT %s
        """,
        (tsquery, tsquery, tsquery, tsquery, tsquery, tsquery, k),
    )
    rows = cur.fetchall()
    cur.close()
    columns = [
        "id", "section_no", "section_heading", "body", "act_name",
        "document_type", "authority_level", "title_id", "compilation_dt", "source_url", "score",
    ]
    return [dict(zip(columns, row)) for row in rows]


def match_rank(rows: list[dict], item: dict) -> int | None:
    targets = [item.get("target_title", ""), *item.get("target_titles", [])]
    targets = [target.lower() for target in targets if target]
    sections = {item["expected_section"]} if item.get("expected_section") else set(item.get("expected_sections", []))
    for rank, row in enumerate(rows[:K], 1):
        title_match = any(target in row.get("act_name", "").lower() for target in targets)
        section_match = not sections or row.get("section_no") in sections
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
    metrics = {
        "label": label,
        "questions": len(in_scope),
        "recall": {
            str(k): sum(1 for item in in_scope if item[f"{label}_rank"] and item[f"{label}_rank"] <= k) / len(in_scope)
            for k in REPORT_K
        },
        "mrr_at_10": sum(1 / rank for rank in ranks) / len(in_scope),
        "ndcg_at_5": sum(
            (1 / math.log2(item[f"{label}_rank"] + 1)) if item[f"{label}_rank"] and item[f"{label}_rank"] <= 5 else 0
            for item in in_scope
        ) / len(in_scope),
        "mean_evidence_coverage": statistics.mean(
            item[f"{label}_coverage"] for item in in_scope
        ),
    }
    metrics["hit_rate_at_5"] = metrics["recall"]["5"]
    metrics["mrr_at_5"] = sum(
        1 / item[f"{label}_rank"] if item[f"{label}_rank"] and item[f"{label}_rank"] <= 5 else 0
        for item in in_scope
    ) / len(in_scope)
    return metrics


def wilson_interval(successes: int, total: int, z: float = 1.96) -> list[float]:
    if not total:
        return [0.0, 0.0]
    p = successes / total
    denominator = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denominator
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total) / denominator
    return [max(0.0, centre - margin), min(1.0, centre + margin)]


def paired_bootstrap_ci(results: list[dict], left_label: str = "fair", repetitions: int = 4000) -> list[float]:
    """95% CI for optimized-minus-left-label Recall@5 on paired questions."""
    in_scope = [item for item in results if item["in_scope"]]
    rng = random.Random(20261120)
    differences = []
    for _ in range(repetitions):
        sample = [rng.choice(in_scope) for _ in in_scope]
        baseline = sum(bool(item[f"{left_label}_rank"] and item[f"{left_label}_rank"] <= 5) for item in sample) / len(sample)
        optimized = sum(bool(item["optimized_rank"] and item["optimized_rank"] <= 5) for item in sample) / len(sample)
        differences.append(optimized - baseline)
    differences.sort()
    return [differences[int(0.025 * repetitions)], differences[int(0.975 * repetitions)]]


def mcnemar_exact(results: list[dict], left_label: str = "fair") -> dict:
    """Paired exact two-sided McNemar test for Recall@5 changes."""
    in_scope = [item for item in results if item["in_scope"]]
    baseline_only = sum(
        bool(item[f"{left_label}_rank"] and item[f"{left_label}_rank"] <= 5)
        and not bool(item["optimized_rank"] and item["optimized_rank"] <= 5)
        for item in in_scope
    )
    optimized_only = sum(
        bool(item["optimized_rank"] and item["optimized_rank"] <= 5)
        and not bool(item[f"{left_label}_rank"] and item[f"{left_label}_rank"] <= 5)
        for item in in_scope
    )
    discordant = baseline_only + optimized_only
    if not discordant:
        p_value = 1.0
    else:
        lower = sum(math.comb(discordant, i) for i in range(min(baseline_only, optimized_only) + 1)) / (2 ** discordant)
        p_value = min(1.0, 2 * lower)
    return {"baseline_only": baseline_only, "optimized_only": optimized_only, "p_value": p_value}


def bucket_metrics(results: list[dict], label: str) -> list[dict]:
    buckets = sorted({item.get("bucket", "unclassified") for item in results if item["in_scope"]})
    output = []
    for bucket in buckets:
        subset = [item for item in results if item["in_scope"] and item.get("bucket", "unclassified") == bucket]
        hits = sum(bool(item[f"{label}_rank"] and item[f"{label}_rank"] <= 5) for item in subset)
        output.append({"bucket": bucket, "n": len(subset), "recall_at_5": hits / len(subset), "ci": wilson_interval(hits, len(subset))})
    return output


def render_report(payload: dict) -> str:
    baseline = payload["retrieval"]["baseline"]
    fair = payload["retrieval"]["fair"]
    optimized = payload["retrieval"]["optimized"]
    hit_delta = optimized["recall"]["5"] - fair["recall"]["5"]
    mrr_delta = optimized["mrr_at_10"] - fair["mrr_at_10"]
    coverage_delta = optimized["mean_evidence_coverage"] - fair["mean_evidence_coverage"]
    refusal = payload["refusal"]
    latency = payload["latency_ms"]
    significance = payload["significance"]
    bucket_rows = "\n".join(
        f"| {row['bucket']} | {row['n']} | {pct(row['recall_at_5'])} | "
        f"{pct(row['ci'][0])}–{pct(row['ci'][1])} |"
        for row in payload["stratified"]["optimized"]
    )
    return f"""# RAG evaluation report

Generated: `{payload['generated_at']}`
Profile: PostgreSQL full-text, title-aware retrieval, no BGE-M3 vectors.

## Fair ablation (`n={payload['questions']['in_scope']}` in-scope)

| Metric | Fair baseline: title/body/heading FTS | Optimized: title-aware + domain-gated FTS | Change |
|---|---:|---:|---:|
| Recall@1 | {pct(fair['recall']['1'])} | {pct(optimized['recall']['1'])} | {(optimized['recall']['1'] - fair['recall']['1']) * 100:+.1f} pp |
| Recall@3 | {pct(fair['recall']['3'])} | {pct(optimized['recall']['3'])} | {(optimized['recall']['3'] - fair['recall']['3']) * 100:+.1f} pp |
| Recall@5 / source hit rate | {pct(fair['recall']['5'])} | {pct(optimized['recall']['5'])} | {hit_delta * 100:+.1f} pp |
| Recall@10 | {pct(fair['recall']['10'])} | {pct(optimized['recall']['10'])} | {(optimized['recall']['10'] - fair['recall']['10']) * 100:+.1f} pp |
| MRR@10 | {fair['mrr_at_10']:.3f} | {optimized['mrr_at_10']:.3f} | {mrr_delta:+.3f} |
| nDCG@5 | {fair['ndcg_at_5']:.3f} | {optimized['ndcg_at_5']:.3f} | {optimized['ndcg_at_5'] - fair['ndcg_at_5']:+.3f} |
| Evidence-term coverage proxy | {pct(fair['mean_evidence_coverage'])} | {pct(optimized['mean_evidence_coverage'])} | {coverage_delta * 100:+.1f} pp |

## Historical baseline comparison

The old body-only PostgreSQL FTS baseline is retained for historical context.
It excludes document titles, so it is not the primary ablation for algorithmic
improvement.

| Metric | Historical body-only FTS | Optimized retrieval | Change |
|---|---:|---:|---:|
| Recall@5 | {pct(baseline['recall']['5'])} | {pct(optimized['recall']['5'])} | {(optimized['recall']['5'] - baseline['recall']['5']) * 100:+.1f} pp |
| MRR@10 | {baseline['mrr_at_10']:.3f} | {optimized['mrr_at_10']:.3f} | {optimized['mrr_at_10'] - baseline['mrr_at_10']:+.3f} |

The fixed set contains `{payload['questions']['total']}` questions from
`{payload['questions']['source']}`: `{payload['questions']['in_scope']}` answerable
and `{payload['questions']['out_of_scope']}` refusal cases. Every answerable
case has one gold source title plus optional section/term checks. Recall is
therefore single-gold source hit rate, not a claim about all workplace-law
questions. It contains `{payload['questions']['alias_cases']}` alias/paraphrase
cases that do not include the complete indexed title. The questions are
deterministic corpus-derived templates; a human-authored golden QA set is still
needed for final Answer Correctness.

## Statistical strength

| Test | Result |
|---|---:|
| Paired bootstrap 95% CI for Recall@5 delta | {pct(significance['bootstrap_ci'][0])} to {pct(significance['bootstrap_ci'][1])} |
| Exact McNemar p-value | {significance['mcnemar']['p_value']:.4f} |
| Optimized-only wins / baseline-only wins | {significance['mcnemar']['optimized_only']} / {significance['mcnemar']['baseline_only']} |

## Stratified optimized Recall@5

| Source bucket | n | Recall@5 | Wilson 95% CI |
|---|---:|---:|---:|
{bucket_rows}

## Refusal and performance

| Metric | Result |
|---|---:|
| Refusal accuracy | {pct(refusal['accuracy'])} ({refusal['correct']}/{refusal['total']}) |
| Refusal accuracy Wilson 95% CI | {pct(refusal['ci'][0])} to {pct(refusal['ci'][1])} |
| False accepts | {refusal['false_accepts']} |
| False refusals | {refusal['false_refusals']} |
| Median retrieval latency | {latency['median']:.1f} ms |
| P95 retrieval latency | {latency['p95']:.1f} ms |

## What is and is not measured

- The offline run measures retrieval, evidence-term coverage, refusal accuracy
  and local latency.
- RAGAS Faithfulness and Answer Correctness are **not** claimed here because
  the default profile does not call an LLM judge. They should be measured in a
  separate online evaluation with a frozen model, prompt and judge set. The
  larger set improves retrieval confidence; it does not turn the evidence-term
  proxy into a Faithfulness score.
- The offline Ask answer is evidence-only and returns source markers; it does
  not silently fabricate a generated legal conclusion.

## Reproduce

```bash
python -m scripts.evaluate_rag --questions {payload['questions']['source']} --report {payload['reports']['report']} --json-report {payload['reports']['json']}
```
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate retrieval and refusal safeguards")
    parser.add_argument("--questions", type=Path, default=QUESTIONS)
    parser.add_argument("--report", type=Path, default=REPORT)
    parser.add_argument("--json-report", type=Path, default=JSON_REPORT)
    parser.add_argument("--latency-repeats", type=int, default=3)
    args = parser.parse_args()
    questions = json.loads(args.questions.read_text())
    conn = psycopg2.connect(config.db_url)
    results = []
    optimized_latencies = []
    refusal_correct = 0
    false_accepts = 0
    false_refusals = 0
    for item in questions:
        started = time.perf_counter()
        baseline = baseline_search(item["question"], conn)
        baseline_ms = (time.perf_counter() - started) * 1000
        fair = fair_title_search(item["question"], conn)
        optimized = lexical_search(item["question"], conn, k=20)
        for _ in range(max(1, args.latency_repeats)):
            started = time.perf_counter()
            lexical_search(item["question"], conn, k=20)
            optimized_latencies.append((time.perf_counter() - started) * 1000)
        result = {
            **item,
            "baseline_rank": match_rank(baseline, item),
            "fair_rank": match_rank(fair, item),
            "optimized_rank": match_rank(optimized, item),
            "baseline_coverage": evidence_coverage(baseline, item),
            "fair_coverage": evidence_coverage(fair, item),
            "optimized_coverage": evidence_coverage(optimized, item),
            "baseline_latency_ms": baseline_ms,
        }
        outcome = answer(item["question"], conn=conn, mode="offline")
        expected_refusal = not item["in_scope"]
        actual_refusal = bool(outcome["refused"])
        if actual_refusal == expected_refusal:
            refusal_correct += 1
        elif expected_refusal:
            false_accepts += 1
        else:
            false_refusals += 1
        result["refused"] = actual_refusal
        result["refusal_reason"] = outcome.get("reason")
        results.append(result)
    conn.close()

    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "profile": "postgres_fts_title_aware_text_only",
        "questions": {
            "total": len(questions),
            "in_scope": sum(q["in_scope"] for q in questions),
            "out_of_scope": sum(not q["in_scope"] for q in questions),
            "source": str(args.questions),
            "alias_cases": sum(q.get("query_style") in {"authority_alias", "party_alias", "industry_alias"} for q in questions),
            "bucket_counts": dict(Counter(q.get("bucket", "unclassified") for q in questions)),
        },
        "reports": {"report": str(args.report), "json": str(args.json_report)},
        "retrieval": {
            "baseline": retrieval_metrics(results, "baseline"),
            "fair": retrieval_metrics(results, "fair"),
            "optimized": retrieval_metrics(results, "optimized"),
        },
        "refusal": {
            "correct": refusal_correct,
            "total": len(questions),
            "accuracy": refusal_correct / len(questions),
            "ci": wilson_interval(refusal_correct, len(questions)),
            "false_accepts": false_accepts,
            "false_refusals": false_refusals,
        },
        "latency_ms": {
            "median": statistics.median(optimized_latencies),
            "p95": percentile(optimized_latencies, 0.95),
        },
        "significance": {
            "bootstrap_ci": paired_bootstrap_ci(results, left_label="fair"),
            "mcnemar": mcnemar_exact(results, left_label="fair"),
        },
        "stratified": {
            "baseline": bucket_metrics(results, "baseline"),
            "optimized": bucket_metrics(results, "optimized"),
        },
        "cases": results,
    }
    args.json_report.parent.mkdir(parents=True, exist_ok=True)
    args.json_report.write_text(json.dumps(payload, indent=2))
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(render_report(payload))
    print(render_report(payload))


if __name__ == "__main__":
    main()

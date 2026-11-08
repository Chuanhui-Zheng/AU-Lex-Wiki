# RAG evaluation report

Generated: `2026-11-19T20:47:06Z`
Profile: PostgreSQL full-text, title-aware retrieval, no BGE-M3 vectors.

## Resume-ready comparison (`n=59` in-scope)

| Metric | Baseline: simple PostgreSQL FTS | Optimized: title-aware + domain-gated FTS | Change |
|---|---:|---:|---:|
| Recall@1 | 1.7% | 66.1% | +64.4 pp |
| Recall@3 | 1.7% | 72.9% | +71.2 pp |
| Recall@5 / source hit rate | 1.7% | 76.3% | +74.6 pp |
| Recall@10 | 1.7% | 79.7% | +78.0 pp |
| MRR@10 | 0.017 | 0.704 | +0.687 |
| nDCG@5 | 0.017 | 0.715 | +0.698 |
| Evidence-term coverage proxy | 8.5% | 100.0% | +91.5 pp |

The fixed set contains `79` questions from
`config/eval_questions_v5_large.json`: `59` answerable
and `20` refusal cases. Every answerable
case has one gold source title plus optional section/term checks. Recall is
therefore single-gold source hit rate, not a claim about all workplace-law
questions. It contains `34` alias/paraphrase
cases that do not include the complete indexed title. The questions are
deterministic corpus-derived templates; a human-authored golden QA set is still
needed for final Answer Correctness.

## Statistical strength

| Test | Result |
|---|---:|
| Paired bootstrap 95% CI for Recall@5 delta | 62.7% to 84.7% |
| Exact McNemar p-value | 0.0000 |
| Optimized-only wins / baseline-only wins | 44 / 0 |

## Stratified optimized Recall@5

| Source bucket | n | Recall@5 | Wilson 95% CI |
|---|---:|---:|---:|
| award | 24 | 87.5% | 69.0%–95.7% |
| decision | 7 | 42.9% | 15.8%–75.0% |
| enterprise_agreement | 6 | 83.3% | 43.6%–97.0% |
| guidance | 10 | 80.0% | 49.0%–94.3% |
| legislation | 12 | 66.7% | 39.1%–86.2% |

## Refusal and performance

| Metric | Result |
|---|---:|
| Refusal accuracy | 100.0% (79/79) |
| Refusal accuracy Wilson 95% CI | 95.4% to 100.0% |
| False accepts | 0 |
| False refusals | 0 |
| Median retrieval latency | 5.9 ms |
| P95 retrieval latency | 212.8 ms |

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
python -m scripts.evaluate_rag --questions config/eval_questions_v5_large.json --report docs/RAG_EVALUATION_V5_LARGE.md --json-report output/rag_evaluation_v5_large.json
```

# RAG evaluation report

Generated: `2026-11-19T20:53:25Z`
Profile: PostgreSQL full-text, title-aware retrieval, no BGE-M3 vectors.

## Fair ablation (`n=59` in-scope)

| Metric | Fair baseline: title/body/heading FTS | Optimized: title-aware + domain-gated FTS | Change |
|---|---:|---:|---:|
| Recall@1 | 10.2% | 66.1% | +55.9 pp |
| Recall@3 | 15.3% | 72.9% | +57.6 pp |
| Recall@5 / source hit rate | 22.0% | 76.3% | +54.2 pp |
| Recall@10 | 32.2% | 79.7% | +47.5 pp |
| MRR@10 | 0.155 | 0.704 | +0.549 |
| nDCG@5 | 0.160 | 0.715 | +0.555 |
| Evidence-term coverage proxy | 100.0% | 100.0% | +0.0 pp |

## Historical baseline comparison

The old body-only PostgreSQL FTS baseline is retained for historical context.
It excludes document titles, so it is not the primary ablation for algorithmic
improvement.

| Metric | Historical body-only FTS | Optimized retrieval | Change |
|---|---:|---:|---:|
| Recall@5 | 1.7% | 76.3% | +74.6 pp |
| MRR@10 | 0.017 | 0.704 | +0.687 |

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
| Paired bootstrap 95% CI for Recall@5 delta | 42.4% to 67.8% |
| Exact McNemar p-value | 0.0000 |
| Optimized-only wins / baseline-only wins | 32 / 0 |

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
| Median retrieval latency | 5.8 ms |
| P95 retrieval latency | 190.9 ms |

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

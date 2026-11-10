# RAG evaluation report

Generated: `2026-11-19T16:57:16Z`  
Profile: PostgreSQL full-text, title-aware retrieval, no BGE-M3 vectors.

## Resume-ready comparison

| Metric | Baseline: simple PostgreSQL FTS | Optimized: title-aware + domain-gated FTS | Change |
|---|---:|---:|---:|
| Recall@5 / source hit rate | 16.7% | 66.7% | +50.0 pp |
| MRR@5 | 0.056 | 0.667 | +0.611 |
| Evidence-term coverage proxy | 41.7% | 91.7% | +50.0 pp |

The comparison uses `6` in-scope questions from
`config/eval_questions_v2.json`; each has one gold document title and optional
section/term checks. “Recall@5” is therefore source hit rate for this single-gold
benchmark, not a claim about all Australian workplace-law questions.

## Refusal and performance

| Metric | Result |
|---|---:|
| Refusal accuracy | 100.0% (8/8) |
| Median retrieval latency | 14.0 ms |
| P95 retrieval latency | 806.4 ms |

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

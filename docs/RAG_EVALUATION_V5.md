# RAG evaluation report

Generated: `2026-11-19T20:07:52Z`  
Profile: PostgreSQL full-text, title-aware retrieval, no BGE-M3 vectors.

## Resume-ready comparison

| Metric | Baseline: simple PostgreSQL FTS | Optimized: title-aware + domain-gated FTS | Change |
|---|---:|---:|---:|
| Recall@5 / source hit rate | 14.3% | 71.4% | +57.1 pp |
| MRR@5 | 0.143 | 0.600 | +0.457 |
| Evidence-term coverage proxy | 35.7% | 85.7% | +50.0 pp |

The comparison uses `7` in-scope questions from
`config/eval_questions_v5.json`; each has one gold document title and optional
section/term checks. “Recall@5” is therefore source hit rate for this single-gold
benchmark, not a claim about all Australian workplace-law questions.

## Refusal and performance

| Metric | Result |
|---|---:|
| Refusal accuracy | 100.0% (9/9) |
| Median retrieval latency | 6.8 ms |
| P95 retrieval latency | 223.4 ms |

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
python -m scripts.evaluate_rag --questions config/eval_questions_v5.json --report docs/RAG_EVALUATION_V5.md --json-report output/rag_evaluation_v5.json
```

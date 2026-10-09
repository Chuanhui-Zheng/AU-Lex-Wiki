# V5 evaluation method

V5 reports reproducible retrieval and refusal metrics for a fixed nine-question
set in `config/eval_questions_v5.json`. Seven questions are in scope and have
one gold source title; two are intentionally out of scope and should be
refused.

## Comparison

The baseline is the pre-V2 PostgreSQL body-only full-text query. The optimized
profile adds title-aware matching, document-domain gating and the current
evidence selection path. Both profiles run against the same local database and
the same question set.

| Metric | Definition | Why it matters |
|---|---|---|
| Recall@5 / source hit rate | Fraction of in-scope questions whose gold source appears in the first five results | Measures whether the answerable source reaches the context window |
| MRR@5 | Mean reciprocal rank of the gold source when it appears in the first five | Rewards putting the right authority near the top |
| Evidence-term coverage | Fraction of expected source terms present in the first five results | Lightweight proxy for whether retrieved evidence contains the needed concept |
| Refusal accuracy | Correct in-scope answers plus correct out-of-scope refusals divided by all questions | Tests the refusal boundary, not just retrieval quality |
| Retrieval latency | Median and P95 time for the optimized local search call | Separates search cost from network/model generation cost |

## Current measured result

The generated report records the current run and is the source of truth for
the exact latency sample:

```bash
python -m scripts.evaluate_rag \
  --questions config/eval_questions_v5.json \
  --report docs/RAG_EVALUATION_V5.md \
  --json-report output/rag_evaluation_v5.json
```

The latest committed comparison is:

| Metric | Baseline | Optimized | Improvement |
|---|---:|---:|---:|
| Recall@5 / source hit rate | 14.3% | 71.4% | +57.1 percentage points |
| MRR@5 | 0.143 | 0.714 | +0.571 |
| Evidence-term coverage proxy | 35.7% | 85.7% | +50.0 percentage points |
| Refusal accuracy | — | 100.0% (9/9) | — |

These are retrieval/evidence metrics on a curated smoke benchmark. They are
not RAGAS Faithfulness or Answer Correctness. Those require a frozen generated
answer set and a separately versioned judge model; V5 does not claim those
numbers.

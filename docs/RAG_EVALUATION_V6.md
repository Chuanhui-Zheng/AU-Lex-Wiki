# V6 Graph-RAG evaluation

Generated: `2026-11-19T20:29:59Z`  
Profile: unified PostgreSQL graph projection over Acts, sections, FWC decisions and Enterprise Agreements.

## Resume-ready comparison

| Metric | Direct one-hop baseline | Bounded Graph-RAG (≤3 hops) | Change |
|---|---:|---:|---:|
| Target path hit rate | 66.7% | 100.0% | +33.3 pp |
| Successful cases | 4/6 | 6/6 | — |
| Median successful path length | 1.0 | 1.0 | +0.0 hops |

The fixed set contains 6 source-linked paths. The baseline
only follows one edge; Graph-RAG follows a bounded directed path and records
the intermediate nodes. This is graph path coverage, not a claim of legal
correctness or generated-answer faithfulness.

## Cases

| Case | Direct hops | Bounded Graph-RAG hops |
|---|---:|---:|
| agreement-to-approval-decision | 1 | 1 |
| agreement-to-clerks-award | 1 | 1 |
| decision-to-fair-work-act-section | miss | 2 |
| decision-to-another-act-section | miss | 2 |
| approval-decision-to-act-section | 1 | 1 |
| act-to-section | 1 | 1 |

## Reproduce

```bash
python -m scripts.evaluate_graph_v6 \
  --cases config/eval_graph_v6.json \
  --report docs/RAG_EVALUATION_V6.md
```

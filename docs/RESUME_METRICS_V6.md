# Resume-ready V6 metrics

Measured on six fixed source-linked paths spanning Enterprise Agreements, FWC
decisions, Acts and sections:

| Metric | Direct one-hop baseline | Bounded Graph-RAG (≤3 hops) | Change |
|---|---:|---:|---:|
| Target path hit rate | 66.7% (4/6) | 100.0% (6/6) | +33.3 pp |
| Median successful path length | 1.0 | 1.0 | 0.0 hops |

## Resume bullet

> Built a bounded temporal Graph-RAG layer over Australian workplace-law
> sources, unifying **17,179 nodes** and **17,692 typed edges** across Acts,
> sections, FWC decisions and Enterprise Agreements; added source-linked
> multi-hop evidence paths, cross-Act resolution and candidate-only override
> detection, improving six-case target path coverage from **66.7% to 100.0%**
> (+33.3 pp) over a direct one-hop baseline.

The path benchmark measures graph connectivity and provenance retrieval. It does
not claim RAGAS Faithfulness, Answer Correctness or complete legal coverage.

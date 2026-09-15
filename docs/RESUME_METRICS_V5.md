# Resume-ready V5 metrics

Measured on the nine-question V5 set: seven in-scope questions covering Acts,
Awards, FWC decisions and Enterprise Agreements, plus two out-of-scope refusal
questions.

| Metric | Simple PostgreSQL FTS | Title-aware + domain-gated retrieval | Change |
|---|---:|---:|---:|
| Recall@5 / source hit rate | 14.3% | 71.4% | +57.1 pp |
| MRR@5 | 0.143 | 0.600 | +0.457 |
| Evidence-term coverage proxy | 35.7% | 85.7% | +50.0 pp |
| Refusal accuracy | — | 100.0% (9/9) | — |

The benchmark also recorded **7.1 ms median** and **230.5 ms P95** local
retrieval latency in the measured run. These are retrieval/evidence metrics;
they are not RAGAS Faithfulness or Answer Correctness.

## Resume bullet

> Extended an evidence-first Australian workplace-law Graph-RAG system with
> six official FWC Enterprise Agreements across Clerks, Retail, Hospitality,
> Professional Employees, Aged Care and Transport; added agreement metadata,
> Award comparison edges and approval-decision links, while improving V5
> single-gold Recall@5 from **14.3% to 71.4%** (+57.1 pp), MRR@5 from
> **0.143 to 0.600**, and evidence-term coverage from **35.7% to 85.7%** with
> **100% (9/9)** refusal accuracy.

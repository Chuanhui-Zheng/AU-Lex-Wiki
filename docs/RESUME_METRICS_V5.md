# Resume-ready V5 metrics

## Expanded benchmark

The original nine-question smoke set is retained in
`docs/RAG_EVALUATION_V5.md`. The release-quality benchmark now contains **79
fixed questions**: 59 answerable cases stratified across legislation, Awards,
FWO guidance, FWC decisions and Enterprise Agreements, plus 20 refusal cases.

| Metric | Fair title/body/heading FTS | Title-aware + domain-gated retrieval | Change |
|---|---:|---:|---:|
| Recall@5 | 22.0% | 76.3% | +54.2 pp |
| Recall@10 | 32.2% | 79.7% | +47.5 pp |
| MRR@10 | 0.155 | 0.704 | +0.549 |
| nDCG@5 | 0.160 | 0.715 | +0.555 |
| Evidence-term coverage proxy | 100.0% | 100.0% | +0.0 pp |
| Refusal accuracy | — | 100.0% (79/79) | — |

The paired bootstrap 95% CI for the fair Recall@5 improvement is **+42.4 to
+67.8 percentage points**; exact paired McNemar `p < 0.0001`. Latency was
measured with three repeated retrieval calls per question: **5.8 ms median**, **190.9 ms
P95**.

This is still an offline retrieval/evidence benchmark. It does not claim RAGAS
Faithfulness or Answer Correctness. The evidence-term proxy was 100% for both
profiles, so it is not presented as an improvement claim.

## Original smoke benchmark

Measured on the nine-question V5 set: seven in-scope questions covering Acts,
Awards, FWC decisions and Enterprise Agreements, plus two out-of-scope refusal
questions.

| Metric | Simple PostgreSQL FTS | Title-aware + domain-gated retrieval | Change |
|---|---:|---:|---:|
| Recall@5 / source hit rate | 14.3% | 71.4% | +57.1 pp |
| MRR@5 | 0.143 | 0.714 | +0.571 |
| Evidence-term coverage proxy | 35.7% | 85.7% | +50.0 pp |
| Refusal accuracy | — | 100.0% (9/9) | — |

The benchmark also recorded **12.3 ms median** and **229.3 ms P95** local
retrieval latency in the measured run. These are retrieval/evidence metrics;
they are not RAGAS Faithfulness or Answer Correctness.

## Resume bullet

> Extended an evidence-first Australian workplace-law Graph-RAG system with
> six official FWC Enterprise Agreements across Clerks, Retail, Hospitality,
> Professional Employees, Aged Care and Transport; added agreement metadata,
> Award comparison edges and approval-decision links, while improving a
> stratified **79-question** V5 benchmark's fair Recall@5 from **22.0% to
> 76.3%** (+54.2 pp), MRR@10 from **0.155 to 0.704**, and nDCG@5 from
> **0.160 to 0.715**, with **100% (79/79)** refusal accuracy and a paired
> bootstrap Recall@5 delta CI of **+42.4 to +67.8 pp**.

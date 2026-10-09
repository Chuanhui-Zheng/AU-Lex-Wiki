# v0.5.0 release scope

V5 adds the first curated Enterprise Agreement layer while preserving the
existing Act, Award, guidance and decision corpus:

- 6 official FWC agreement PDFs;
- 241 agreement chunks;
- 6 Award comparison edges;
- 1 resolved FWC approval-decision edge;
- 6 industry slices: Clerks, Retail, Hospitality, Professional Employees,
  Aged Care and Transport;
- 0 stored vectors in the default text-only profile;
- V5 retrieval/refusal report and agreement-specific API/UI.

The final nine-question benchmark reports Recall@5/source hit rate of 14.3% →
71.4% (+57.1 pp), MRR@5 of 0.143 → 0.714 (+0.571), evidence-term coverage of
35.7% → 85.7% (+50.0 pp), and refusal accuracy of 100% (9/9). Local retrieval
latency in that run was 12.3 ms median and 229.3 ms P95.

Bulk agreement coverage, historical variation chains and automated Award-vs-
Agreement conflict analysis remain V6 Graph-RAG work.

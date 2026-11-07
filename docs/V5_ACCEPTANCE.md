# V5 acceptance checklist

- [x] Six official FWC agreement PDFs are represented across six industries.
- [x] Agreement PDFs are validated by their `%PDF` signature before parsing.
- [x] 241 agreement chunks are indexed as `document_type=enterprise_agreement`.
- [x] Agreement metadata stores industry, employer, matter, version, dates and status.
- [x] Six Agreement→Award `compares_to` edges resolve to indexed Award nodes.
- [x] Apple Agreement→FWC approval decision `approved_by` edge resolves to
  `[2023] FWCFB 185`.
- [x] Agreement pages and APIs expose source-linked metadata and graph edges.
- [x] Agreement questions retrieve agreement evidence in offline Ask mode.
- [x] Out-of-scope questions remain refused.
- [x] Expanded V5 benchmark contains 79 unique questions across six source
  buckets and 20 refusal cases.
- [x] V5 benchmark reports Recall@1/3/5/10, MRR@10, nDCG@5, evidence coverage,
  Wilson intervals, paired bootstrap CI, McNemar significance, refusal and
  repeated latency.
- [x] BGE-M3 dense and sparse vectors remain empty in the default profile.

Run the acceptance suite with one command:

```bash
python -m scripts.run_v5_acceptance
```

The runner validates official FWC provenance, agreement/chunk completeness,
exact release counts, API filtering and graph resolution. The retrieval
benchmark is intentionally separate because it rewrites its generated report
and latency sample:

```bash
python -m scripts.evaluate_rag \
  --questions config/eval_questions_v5_large.json \
  --report docs/RAG_EVALUATION_V5_LARGE.md \
  --json-report output/rag_evaluation_v5_large.json
```

The original nine-question smoke report remains at
`docs/RAG_EVALUATION_V5.md`; use `docs/RAG_EVALUATION_V5_LARGE.md` for the
resume/release metric.

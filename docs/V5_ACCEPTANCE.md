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
- [x] V5 benchmark reports Recall@5, MRR@5, evidence coverage, refusal and latency.
- [x] BGE-M3 dense and sparse vectors remain empty in the default profile.

Run the acceptance suite with:

```bash
python -m scripts.check_agreements
python -m scripts.check_v5_api_contract
python -m scripts.smoke_v5
```

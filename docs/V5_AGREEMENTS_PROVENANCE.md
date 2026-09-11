# V5 Enterprise Agreement provenance

V5 adds six official Fair Work Commission agreement PDFs, one per requested
industry slice:

| Industry | FWC agreement | Agreement ID |
|---|---|---|
| Clerks | Ray White Mt Gravatt Enterprise Agreement 2024 | AE524636 |
| Retail | Apple Australia National Enterprise Agreement 2023 | AE521821 |
| Hospitality | Compass Group ESS Offshore Oil & Gas (BW Offshore) Enterprise Agreement 2025 | AE529157 |
| Professional Employees | Academic and Professional Employees Enterprise Agreement 2024 | AE525456 |
| Aged Care | Boneham Aged Care Services Inc Aged Care Sector Employees Enterprise Agreement 2025 | AE531730 |
| Transport | Border Express Pty Ltd Transport Employees and TWU Sydney, Newcastle and Central Coast Site Agreement 2024 | AE524557 |

The manifest is [`config/agreements_v5.json`](../config/agreements_v5.json).
The downloader uses the official `documents/agreements/approved/ae*.pdf`
endpoints with a normal browser User-Agent and rejects non-PDF responses. The
parser uses `pypdf`, preserves the source URL and splits the agreement into
clause-oriented chunks. No text is hand-copied.

The graph stores:

```text
Agreement --compares_to--> Modern Award
Agreement --approved_by---> FWC approval decision
```

Metadata includes employer, industry, FWC matter number, version, approval
date, nominal expiry and publication status. A nominal expiry is metadata, not
an assertion that the agreement has ceased; the source status and current FWC
publication must still be checked.

## Reproduce

```bash
python -m scripts.ingest_agreements
python -m scripts.check_agreements
python -m scripts.check_v5_api_contract
python -m scripts.smoke_v5
```

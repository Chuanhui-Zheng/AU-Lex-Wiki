# V5 Enterprise Agreement API

```http
GET /api/agreements
GET /api/agreements?industry=Retail
GET /api/agreement/AE521821
GET /agreements
GET /agreement/AE521821
```

The list endpoint returns agreement ID, title, industry, employer, approval
date, nominal expiry, publication status, official PDF URL and graph-edge
count. The detail endpoint adds typed references to the compared Award and any
indexed FWC approval decision.

Agreement evidence returned by `/api/chat` includes `agreement_id`, so the Ask
panel can link directly to `/agreement/{agreement_id}` instead of sending a
user to an ambiguous section route.

The endpoint exposes indexed provenance and does not infer that a nominally
expired agreement is legally terminated. Current status must be checked with
the official FWC publication.

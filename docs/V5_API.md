# V5 Enterprise Agreement API

```http
GET /api/agreements
GET /api/agreements?industry=Retail
GET /api/agreements?status=published
GET /api/agreements?industry=Retail&status=published
GET /api/agreement/AE521821
GET /agreements
GET /agreement/AE521821
```

The list endpoint returns agreement ID, title, industry, employer, approval
date, nominal expiry, publication status, official PDF URL and graph-edge
count. The detail endpoint adds typed references to the compared Award and any
indexed FWC approval decision.

`industry` and `status` are case-insensitive exact filters. The status filter
is a publication-state field from the selected FWC metadata (`published`,
`current`, `expired`, `terminated` or `unknown`); it is not a legal opinion
about whether an agreement still applies to a particular employee.

Agreement evidence returned by `/api/chat` includes `agreement_id`, so the Ask
panel can link directly to `/agreement/{agreement_id}` instead of sending a
user to an ambiguous section route.

The endpoint exposes indexed provenance and does not infer that a nominally
expired agreement is legally terminated. Current status must be checked with
the official FWC publication.

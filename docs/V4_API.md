# V4 decision API

The decision layer is available without leaving the existing FastAPI app:

```http
GET /api/decisions
GET /api/decisions?category=unfair_dismissal
GET /api/decision/2024-fwcfb-458
GET /decisions
GET /decision/2024-fwcfb-458
```

`/api/decisions` returns decision metadata and the number of graph edges. The
detail endpoint returns typed `cites`, `interprets` and `concerns` references,
including the linked Act/Award name, section or clause, agreement label and
source citation. The HTML pages are intentionally simple server-rendered
shells: the browser fetches the same JSON, so the UI and API cannot drift into
two different decision definitions.

The endpoint exposes provenance only. It does not make a decision binding,
replace a current instrument, or turn a case summary into legal advice.

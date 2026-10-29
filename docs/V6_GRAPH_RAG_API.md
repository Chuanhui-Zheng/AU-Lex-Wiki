# V6 Graph-RAG API

V6 adds a unified read projection over the existing source-specific tables.
Ingestion remains source-specific; `graph_nodes` and `graph_edges` provide a
bounded traversal surface for evidence paths.

## Path endpoint

```http
GET /api/graph/path?start=agreement:AE521821&target_type=decision&max_hops=3
GET /api/graph/path?start=section:16659&target_type=section&as_of=2025-01-01
```

Parameters:

- `start` — a graph node key such as `section:16659`, `agreement:AE521821`,
  `decision:2023-fwcfb-185` or `act:C2009A00028`;
- `target` — optional exact node key;
- `target_type` — optional node type filter (`act`, `section`, `decision`, or
  `agreement`);
- `max_hops` — bounded to 1–5, default 3;
- `as_of` — optional ISO date applied to edge validity intervals.

The response contains ordered nodes and edges, including official source URLs,
relation types, evidence text and validity dates. A missing path returns an
empty `paths` array; it does not invent a relationship.

## Conflict candidates

```http
GET /api/graph/conflicts
GET /api/graph/conflicts?as_of=2025-01-01
```

This endpoint returns only explicitly typed `overrides` or `varies` edges. The
response is labelled `candidate_only`: an override edge is a review signal,
not an automatic legal conclusion that two provisions conflict.

## Graph-RAG Ask behavior

When `ENABLE_GRAPH_RAG=true`, Ask keeps the strongest direct retrieval results
and adds at most `GRAPH_CONTEXT_SECTIONS` sections reachable within
`GRAPH_MAX_HOPS`. Containment edges are excluded from expansion to prevent an
Act node from flooding the prompt with every section. Expanded evidence is
marked with its graph hop count and still passes the existing citation and
refusal checks.

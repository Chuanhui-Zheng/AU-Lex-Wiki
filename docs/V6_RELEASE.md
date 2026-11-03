# v0.6.0 release scope

V6 turns the V1–V5 source-specific relations into an auditable Graph-RAG read
projection:

- 17,179 graph nodes: 288 Acts, 16,878 sections, 7 FWC decisions and 6
  Enterprise Agreements;
- 17,692 graph edges, including 16,878 containment edges, 723 cross-Act edges,
  47 definition edges, 21 override edges, 11 citation edges, 6 Award comparison
  edges and 1 approval edge;
- bounded `/api/graph/path` traversal with `max_hops` and `as_of` controls;
- graph-backed Ask expansion capped by `GRAPH_MAX_HOPS` and
  `GRAPH_CONTEXT_SECTIONS`;
- timeline and candidate-only conflict APIs;
- UI evidence-path panels for agreements and FWC decisions.

The six-case path benchmark improved one-hop target coverage from **66.7% (4/6)**
to **100.0% (6/6)** with bounded paths up to three hops (+33.3 pp). This is
graph path coverage, not RAGAS Faithfulness or a legal correctness claim.

V6 does not claim complete Australian employment-law coverage. Unresolved
references remain visible and are never silently converted into evidence.

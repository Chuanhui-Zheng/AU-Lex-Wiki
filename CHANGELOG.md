# Changelog

## v0.6.0 — Graph-RAG foundation

- added a unified temporal graph projection over Acts, sections, decisions and
  Enterprise Agreements;
- added bounded path, timeline and candidate-conflict APIs with source URLs;
- added cross-Act reference resolution and graph-backed Ask expansion;
- rendered evidence paths on agreement and decision pages;
- added a direct-versus-multi-hop benchmark and deterministic V6 acceptance suite.

## v0.5.0 — Enterprise Agreements

- added six official FWC agreement PDFs across six industries;
- added agreement metadata for employer, industry, matter, version, approval,
  nominal expiry and status;
- added clause-oriented agreement chunks and text-only ingestion;
- added Agreement→Award comparison edges and an Agreement→approval decision
  edge;
- added agreement list/detail API and graph pages;
- added V5 retrieval, evidence coverage and refusal benchmark.

## v0.4.0 — V4 FWC decisions

- added a curated six-decision Fair Work Commission source set;
- added PDF fetch, parsing, text-only ingestion and provenance checks;
- added `decisions` and `decision_refs` graph tables;
- added `cites`, `interprets` and `concerns` edges;
- improved case-caption retrieval for partial party-name questions;
- added `/decisions` and `/decision/{decision_id}` inspection pages;
- added V4 retrieval/refusal benchmark and resume-ready measured metrics;
- kept BGE-M3 embeddings disabled by default, with zero stored vectors in the
  accepted V4 local profile.

# Changelog

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

# V4 acceptance checklist

- [x] Six curated decisions are listed in the reviewable V4 manifest.
- [x] Official FWC PDF sources are cached and parsed into 228 decision chunks.
- [x] Decision metadata stores citation, date, category and source URL.
- [x] Act citation edges are linked in `decision_refs`.
- [x] Verified Award references create `interprets` edges.
- [x] Enterprise agreement decisions create `concerns` edges.
- [x] Decision case-caption queries retrieve decision evidence in offline mode.
- [x] Out-of-scope questions remain refused.
- [x] `/decisions` and `/decision/{decision_id}` expose the graph in the UI.
- [x] V4 retrieval metrics are recorded in `docs/RAG_EVALUATION_V4.md`.
- [x] The default profile has zero stored dense or sparse vectors.

The acceptance run is reproducible with:

```bash
python -m scripts.check_decision_manifest
python -m scripts.check_v4_counts
python -m scripts.smoke_v4
```

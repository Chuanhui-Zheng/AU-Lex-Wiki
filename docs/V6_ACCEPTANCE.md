# V6 acceptance checklist

- [x] A unified `graph_nodes` / `graph_edges` projection covers Acts, sections,
  FWC decisions and Enterprise Agreements.
- [x] Nodes and edges carry source URLs and temporal validity metadata where the
  upstream record provides dates.
- [x] Cross-Act references are resolved to latest parent section nodes while
  preserving the raw subsection identifier.
- [x] Bounded graph paths are exposed by `/api/graph/path` and shown on
  Agreement and decision pages.
- [x] Ask adds bounded graph evidence without replacing direct retrieval.
- [x] Override/variation results are labelled candidate-only by the conflicts
  endpoint.
- [x] Direct-vs-multi-hop benchmark is recorded in `docs/RAG_EVALUATION_V6.md`.

Final local projection count: **17,179 nodes**, **17,692 edges**, **0 dangling
nodes**, **0 inverted validity intervals**. The final benchmark reaches **6/6**
bounded path hits versus **4/6** for the one-hop baseline.

Run deterministic checks with:

```bash
python -m scripts.run_v6_acceptance
```

Regenerate the measured path benchmark separately:

```bash
python -m scripts.evaluate_graph_v6 \
  --cases config/eval_graph_v6.json \
  --report docs/RAG_EVALUATION_V6.md
```

# V4 FWC decision provenance

V4 adds a deliberately small, reviewable set of six Fair Work Commission
decisions. It is a seed set for decision retrieval, not a claim of complete
case-law coverage.

| Decision family | Records | Official publisher |
|---|---:|---|
| Annual Wage Review | 2 | Fair Work Commission |
| General protections | 1 | Fair Work Commission |
| Unfair dismissal | 1 | Fair Work Commission |
| Enterprise agreement approval | 2 | Fair Work Commission |

The manifest is [`config/decisions_v4.json`](../config/decisions_v4.json).
The fetcher stores the official PDF under `data/raw/decisions/`, the parser
creates paragraph-sized JSONL chunks, and ingestion stores each decision as
`document_type=decision` with `authority_level=decision`.

Each decision also gets a graph record. `decision_refs` can link a decision to:

```text
Decision --cites------> Fair Work Act section
Decision --interprets-> Modern Award / clause
Decision --concerns---> Enterprise Agreement
```

The source URL, citation and date remain attached to the decision node. The
database and raw documents are local artifacts and are intentionally excluded
from Git; another user can reproduce them with the manifest and fetch command.

## Reproduce

```bash
python -m scripts.fetch_decisions
python -m scripts.parse_decisions
python -m scripts.embed_and_ingest --skip-embedding
python -m scripts.link_decisions
python -m scripts.check_decisions
```

The browser-exported PDFs are only a fallback for the six official URLs when a
local environment is challenged by the FWC anti-bot layer. They are not
rewritten or hand-copied into the corpus.

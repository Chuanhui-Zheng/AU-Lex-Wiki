# V2 data provenance

Modern Awards are collected from the official Fair Work Ombudsman Award index
and the linked Fair Work Commission award publication pages. Pay Guides are
downloaded from the official Fair Work Ombudsman `AwardSummary` endpoint as
DOCX files.

The pipeline writes raw source files under `data/raw/`, then creates JSONL
chunks under `data/chunks/`. These generated files are intentionally ignored by
Git. A fresh checkout can reproduce them by running:

```bash
python -m scripts.fetch_awards
python -m scripts.check_awards
python -m scripts.parse_awards
python -m scripts.embed_and_ingest --skip-embedding
```

Every stored record keeps its official source URL, document type, publisher,
and retrieval timestamp where available. `award` is the instrument;
`pay_guide` is `official_guidance` and must be cited as explanatory material.

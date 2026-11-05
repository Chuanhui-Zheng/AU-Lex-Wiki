# V5 evaluation files

The release-quality V5 metrics are committed as Markdown, so they can be
opened directly in GitHub, VS Code or any Markdown viewer:

- [Expanded evaluation report](RAG_EVALUATION_V5_LARGE.md) — full tables,
  fair baseline, historical baseline, confidence intervals, significance,
  stratified results and latency.
- [Resume metrics](RESUME_METRICS_V5.md) — condensed version for a CV.
- [Fixed 79-question set](../config/eval_questions_v5_large.json) — 59
  answerable questions, 20 refusal questions and 34 alias/paraphrase cases.
- [Evaluation runner](../scripts/evaluate_rag.py) — regenerates the report.

## Open or regenerate

From the repository root:

```bash
open docs/RAG_EVALUATION_V5_LARGE.md
python -m scripts.evaluate_rag
```

The generated raw JSON is written to
`output/rag_evaluation_v5_large.json`. It is intentionally ignored as a local
build artifact; the committed Markdown report is the reviewable release
artifact. The report is reproducible from the fixed question set and the local
PostgreSQL snapshot.

# Resume-ready project metrics

Use the measured values from [`RAG_EVALUATION.md`](RAG_EVALUATION.md), and
rerun the evaluator after changing the corpus or retrieval code.

> Built an Australian workplace-law RAG system over Fair Work legislation,
> Modern Awards and official FWO guidance. On a six-question single-gold
> retrieval benchmark, title-aware, domain-gated PostgreSQL retrieval improved
> source hit rate at Recall@5 from **16.7% to 66.7%** (+50.0 pp), MRR@5 from
> **0.056 to 0.667**, and evidence-term coverage from **41.7% to 91.7%**.
> The offline refusal gate achieved **100% (8/8)** on the included in-scope and
> out-of-scope questions, with **14.0 ms median** and **806.4 ms P95** local
> retrieval latency.

These are retrieval/evidence metrics, not RAGAS Faithfulness or Answer
Correctness. Those two require a fixed generated-answer set and an LLM judge;
the project report explicitly leaves them unclaimed until that online protocol
is run.

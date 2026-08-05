# Resume-ready project metrics

Use the measured values from [`RAG_EVALUATION_V4.md`](RAG_EVALUATION_V4.md), and
rerun the evaluator after changing the corpus or retrieval code.

> Built an Australian workplace-law RAG system over Fair Work legislation,
> Modern Awards, FWO guidance and curated FWC decisions. On a seven-question
> single-gold retrieval benchmark, title-aware, domain-gated PostgreSQL
> retrieval improved source hit rate at Recall@5 from **28.6% to 71.4%**
> (+42.9 pp), MRR@5 from **0.286 to 0.714**, and evidence-term coverage from
> **50.0% to 92.9%**. The offline refusal gate achieved **100% (9/9)** on the
> included in-scope and out-of-scope questions, with **4.8 ms median** and
> **216.3 ms P95** local retrieval latency in the measured run.

These are retrieval/evidence metrics, not RAGAS Faithfulness or Answer
Correctness. Those two require a fixed generated-answer set and an LLM judge;
the project report explicitly leaves them unclaimed until that online protocol
is run.

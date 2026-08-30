# Resume bullet — V4 decision layer

Built an evidence-first Graph-RAG system for Australian workplace law over
Fair Work legislation, 122 Modern Awards, 121 Pay Guides, official FWO
guidance and six curated FWC decisions; improved single-gold source hit rate
from **28.6% to 71.4%** at Recall@5 (+42.9 pp) and MRR@5 from **0.286 to
0.714** by adding title-aware, domain-gated PostgreSQL retrieval, while
maintaining **100% (9/9)** refusal accuracy on the measured scope set and
linking every decision answer to typed Act/Award/agreement evidence.

Interview-safe clarification: these are offline retrieval and refusal metrics,
not RAGAS Faithfulness or Answer Correctness. The benchmark definition and
reproduction command are in [`EVALUATION_PROTOCOL.md`](EVALUATION_PROTOCOL.md).

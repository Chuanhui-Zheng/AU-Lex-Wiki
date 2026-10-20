# AU-WorkLaw-Atlas ingestion roadmap

**Current baseline:** V1 federal workplace-law core is implemented with the
Fair Work Act, Fair Work Regulations, PostgreSQL full-text retrieval, grounded
Ask, and clause-level reference extraction.

## V1 — Federal legal core

- Fair Work Act 2009 from the Federal Register of Legislation;
- Fair Work Regulations 2009 and related federal instruments;
- version metadata, effective dates and official source URLs;
- clause-level parsing, hybrid retrieval and citation-gated answers.

## V2 — Awards and pay conditions

- 122 current Modern Awards from the Fair Work Ombudsman catalogue;
- Award HTML clauses, tables and variation-history blocks from the official
  Fair Work Commission award publication;
- 121 available Fair Work Ombudsman Pay Guide DOCX files, parsed without a
  third-party office suite;
- separate `award` and `pay_guide` nodes with authority-level metadata;
- section/clause retrieval with title-aware PostgreSQL full-text ranking;
- offline evidence answers and refusal for questions outside workplace-law
  terminology.

The V2 graph boundary is now explicit:

```text
Fair Work Act / Regulations -> Modern Award -> Award clause -> Pay Guide
```

The current ingestion remains text-only by default. BGE-M3 dense and sparse
vectors remain an optional upgrade and are not required for the V2 corpus.

## V3 — Official explanations

- Fair Work Ombudsman Workplace Guides, including the Fair Work Handbook;
- Fact Sheets and Best Practice Guides published on the official FWO site;
- independent guidance documents with `authority_level=official_guidance`;
- evidence responses that expose whether a source is primary law, an Award,
  a Pay Guide or official guidance.

V3 does not promote an FWO explanation to the status of legislation. It is
retrieved to explain practical conditions, while the answer continues to show
the underlying source URL and authority label.

## V4 — Decisions

- six curated Fair Work Commission decisions before bulk ingestion;
- decision metadata, case type, date, official PDF and cited provisions;
- paragraph-level decision evidence in the same grounded Ask pipeline;
- `Decision -> cites -> Act section`, `Decision -> interprets -> Award` and
  `Decision -> concerns -> Enterprise Agreement` graph edges;
- `/decisions`, `/decision/{decision_id}`, `/api/decisions` and
  `/api/decision/{decision_id}` for source-linked inspection;
- V4 retrieval benchmark including decision questions and refusal checks.

V4 is intentionally a curated interpretation layer. It should grow through a
reviewed manifest rather than silently treating every search result as binding
precedent.

## V5 — Agreements

- six selected official Enterprise Agreements across Clerks, Retail,
  Hospitality, Professional Employees, Aged Care and Transport;
- agreement PDF clause parsing with approval, nominal expiry, version, employer,
  matter number and publication-status metadata;
- `Agreement -> compares_to -> Modern Award` edges;
- `Agreement -> approved_by -> FWC decision` edges;
- agreement-specific Ask evidence, API endpoints and graph pages;
- a V5 benchmark covering agreement retrieval and refusal safeguards.

V5 remains a curated industry slice. It is a comparison layer, not a claim
that every Australian enterprise agreement is indexed.

## V6 — Graph-RAG

当前已开始实现统一时序图投影和有界路径检索：

- `graph_nodes` / `graph_edges` 统一 Act、section、decision、agreement 节点；
- 节点和边携带 `valid_from` / `valid_to` 与官方来源；
- `/api/graph/path` 返回可审计的多跳证据链；
- Ask 保留直接召回，并在 `GRAPH_MAX_HOPS` 范围内补充图谱证据。

后续再做复杂能力：

- cross-source reference resolution;
- temporal validity checks;
- definition, exception, override and delegation edges;
- multi-hop retrieval with an evidence path rendered in the UI.

The project must not claim complete Australian employment-law coverage. Each answer reports the indexed source set and refuses when the evidence does not support the requested conclusion.

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

- curated Fair Work Commission decisions before bulk ingestion;
- decision metadata, case type, date and cited provisions;
- links from a decision to the Award, Agreement or Act provisions it interprets.

## V5 — Agreements

- selected Enterprise Agreements by industry first;
- approval, nominal expiry, variation and termination metadata;
- comparison against the relevant Modern Award;
- privacy and publication-status checks before indexing.

## V6 — Graph-RAG

- cross-source reference resolution;
- temporal validity checks;
- definition, exception, override and delegation edges;
- multi-hop retrieval with an evidence path rendered in the UI.

The project must not claim complete Australian employment-law coverage. Each answer reports the indexed source set and refuses when the evidence does not support the requested conclusion.

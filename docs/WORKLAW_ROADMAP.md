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

- current Modern Awards from Fair Work Commission document search;
- award variation history and historical versions;
- Fair Work Ombudsman pay guides;
- award clause, classification, allowance and penalty-rate relations.

## V3 — Official explanations

- Fair Work Ombudsman workplace guides and fact sheets;
- source type and authority-level labels;
- links from a legal provision to the official explanation that discusses it.

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

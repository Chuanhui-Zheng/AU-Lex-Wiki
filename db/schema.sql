-- AU-WorkLaw-Atlas: PostgreSQL schema
-- Requires: pgvector extension

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ─────────────────────────────────────────────
-- Acts / Titles
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS acts (
    id              bigserial PRIMARY KEY,
    title_id        text UNIQUE NOT NULL,     -- Register API titleId
    name            text NOT NULL,
    series_id       text,
    status          text DEFAULT 'inforce',   -- inforce | repealed
    year            int,
    source_url      text,
    fetched_at      timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_acts_name ON acts(name);
CREATE INDEX IF NOT EXISTS idx_acts_year ON acts(year);

-- ─────────────────────────────────────────────
-- Compilations (point-in-time versions of an Act)
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS compilations (
    id              bigserial PRIMARY KEY,
    act_id          bigint NOT NULL REFERENCES acts(id) ON DELETE CASCADE,
    document_id     text UNIQUE NOT NULL,     -- Register API documentId
    compilation_dt  date NOT NULL,
    is_latest       boolean DEFAULT false,
    xml_path        text,                     -- local path to downloaded XML
    fetched_at      timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_compilations_act ON compilations(act_id);
CREATE INDEX IF NOT EXISTS idx_compilations_dt  ON compilations(compilation_dt);

-- ─────────────────────────────────────────────
-- Sections (clause-level chunks)
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sections (
    id              bigserial PRIMARY KEY,
    compilation_id  bigint NOT NULL REFERENCES compilations(id) ON DELETE CASCADE,
    act_id          bigint NOT NULL REFERENCES acts(id) ON DELETE CASCADE,
    eid             text,                     -- AkomaNtoso eId, e.g. "sec_18__subsec_1"
    section_no      text NOT NULL,            -- display: "18(1)"
    section_heading text,
    parent_no       text,                     -- parent section for subsections
    depth           int DEFAULT 0,            -- 0=section, 1=subsection, 2=paragraph
    body            text NOT NULL,
    body_tsv        tsvector GENERATED ALWAYS AS (
                        to_tsvector('english', body)
                    ) STORED,
    embedding       vector(1024),
    sparse_weights  jsonb,                    -- BGE-M3 lexical_weights {token_id: weight}
    char_count      int GENERATED ALWAYS AS (char_length(body)) STORED,
    source_url      text
);

CREATE INDEX IF NOT EXISTS idx_sections_hnsw ON sections
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE INDEX IF NOT EXISTS idx_sections_fts   ON sections USING gin(body_tsv);
CREATE INDEX IF NOT EXISTS idx_sections_act   ON sections(act_id);
CREATE INDEX IF NOT EXISTS idx_sections_comp  ON sections(compilation_id);
CREATE INDEX IF NOT EXISTS idx_sections_no    ON sections(section_no);
CREATE INDEX IF NOT EXISTS idx_sections_trgm  ON sections USING gin(section_no gin_trgm_ops);

-- ─────────────────────────────────────────────
-- Cross-references between sections
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS section_refs (
    id              bigserial PRIMARY KEY,
    from_section_id bigint NOT NULL REFERENCES sections(id) ON DELETE CASCADE,
    to_section_id   bigint REFERENCES sections(id) ON DELETE SET NULL,
    to_act_name     text,                     -- if ref targets a different Act
    to_section_no   text,                     -- resolved section number
    ref_text        text,                     -- raw text: "under section 30EK"
    ref_type        text NOT NULL             -- cross_ref | definition | delegation | override
        CHECK (ref_type IN ('cross_ref','definition','delegation','override','other'))
);

CREATE INDEX IF NOT EXISTS idx_refs_from ON section_refs(from_section_id);
CREATE INDEX IF NOT EXISTS idx_refs_to   ON section_refs(to_section_id);

-- ─────────────────────────────────────────────
-- Entities extracted from sections
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS entities (
    id              bigserial PRIMARY KEY,
    section_id      bigint NOT NULL REFERENCES sections(id) ON DELETE CASCADE,
    entity_type     text NOT NULL             -- definition | obligation | prohibition | delegation | party
        CHECK (entity_type IN ('definition','obligation','prohibition','delegation','party','penalty')),
    term            text,                     -- defined term or party name
    body            text NOT NULL,            -- extracted sentence / clause
    confidence      float DEFAULT 1.0
);

CREATE INDEX IF NOT EXISTS idx_entities_section ON entities(section_id);
CREATE INDEX IF NOT EXISTS idx_entities_type    ON entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_entities_term    ON entities USING gin(to_tsvector('english', coalesce(term,'')));

-- ─────────────────────────────────────────────
-- Eval set (auto-generated QA pairs)
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS eval_questions (
    id              bigserial PRIMARY KEY,
    question        text NOT NULL,
    expected_answer text NOT NULL,
    source_section_ids bigint[],
    question_type   text NOT NULL
        CHECK (question_type IN ('locate','cross_ref','temporal','refusal')),
    act_name        text,
    created_at      timestamptz DEFAULT now()
);

-- =============================================================================
-- Minerva Lab — Postgres schema (Tier: relational citizen records + pgvector)
-- Runs once on an empty data dir (docker-entrypoint-initdb.d). A clean-state
-- reset drops the volume so this re-runs from scratch (§6).
--
-- Postgres plays two roles (§2.1): the relational SQL-injection target
-- (citizens / portal_users, T1190) AND the RAG vector store (rag_chunks).
-- All data is FABRICATED — no real PII (§7).
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS vector;

-- ---- Relational citizen records (the SQLi target surface, T1190) ------------
CREATE TABLE citizens (
    citizen_id      SERIAL PRIMARY KEY,
    full_name       TEXT NOT NULL,
    dob             DATE,
    county          TEXT,
    benefit_program TEXT,
    status          TEXT,
    state_id        TEXT,          -- synthetic state identifier
    email           TEXT
);

-- Portal credential store. Separate table so a UNION-based injection has a
-- meaningful secondary target (weak hashes are intentional — research target).
CREATE TABLE portal_users (
    username        TEXT PRIMARY KEY,
    password_md5    TEXT NOT NULL,  -- deliberately weak (unsalted MD5) — T1190 loot
    role            TEXT NOT NULL,
    federal_scope   BOOLEAN DEFAULT FALSE
);

-- ---- RAG vector store (pgvector) — the ATLAS pivot target (§2.1) ------------
-- Dimensionless `vector` column so any Ollama embed model works without DDL
-- changes; the application enforces EMBED_DIM consistency at insert time.
-- Corpus is small, so a sequential scan with <=> is fine (no ANN index needed).
CREATE TABLE rag_chunks (
    id          SERIAL PRIMARY KEY,
    doc_id      INTEGER NOT NULL,         -- maps back to MySQL docstore.documents.id
    source      TEXT NOT NULL,
    content     TEXT NOT NULL,
    embedding   vector NOT NULL,
    indexed_at  TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_rag_chunks_doc ON rag_chunks (doc_id);

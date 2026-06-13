-- =============================================================================
-- Minerva Lab — MySQL document store (RAG ingestion source, dual-role layer)
-- Uploaded documents (Tier 2 /upload) and the seed corpus land here; the
-- rag-ingest job embeds them into pgvector. This is the ingestion source the
-- ATLAS poisoning vector targets (AML.T0020). Runs once on init.
-- =============================================================================

CREATE TABLE IF NOT EXISTS documents (
    id        INT AUTO_INCREMENT PRIMARY KEY,
    title     VARCHAR(255) NOT NULL,
    source    VARCHAR(255) NOT NULL,         -- e.g. seed:foo.md or upload:bar.txt
    body      MEDIUMTEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_source (source)
);

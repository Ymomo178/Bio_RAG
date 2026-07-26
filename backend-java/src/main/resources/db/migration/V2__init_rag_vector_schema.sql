-- 启用 pgvector，并建立与业务知识库解耦的 RAG 文本块表。
CREATE EXTENSION IF NOT EXISTS vector;

CREATE SCHEMA IF NOT EXISTS rag;

CREATE TABLE rag.document_chunks (
    chunk_id TEXT PRIMARY KEY,
    knowledge_base_id UUID REFERENCES business.knowledge_bases(id),
    document_version_id UUID REFERENCES business.document_versions(id),
    chunk_index INTEGER NOT NULL,
    source_id VARCHAR(255) NOT NULL,
    normalized_path VARCHAR(1024) NOT NULL,
    document_title VARCHAR(1024),
    section TEXT,
    page_number INTEGER,
    content TEXT NOT NULL,
    embedding_text TEXT NOT NULL,
    image_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    model_name VARCHAR(255) NOT NULL,
    embedding vector(1024) NOT NULL,
    search_vector TSVECTOR GENERATED ALWAYS AS (
        to_tsvector('simple', coalesce(embedding_text, ''))
    ) STORED,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_document_chunks_knowledge_base
    ON rag.document_chunks(knowledge_base_id);

CREATE INDEX idx_document_chunks_document_version
    ON rag.document_chunks(document_version_id);

CREATE INDEX idx_document_chunks_search_vector
    ON rag.document_chunks USING GIN(search_vector);

CREATE INDEX idx_document_chunks_embedding_hnsw
    ON rag.document_chunks USING hnsw (embedding vector_cosine_ops);

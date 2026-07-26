CREATE TABLE business.conversations (
    id UUID PRIMARY KEY,
    owner_id UUID NOT NULL REFERENCES business.users(id) ON DELETE CASCADE,
    knowledge_base_id UUID REFERENCES business.knowledge_bases(id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_conversations_owner_updated
    ON business.conversations(owner_id, updated_at DESC);

CREATE TABLE business.chat_messages (
    id UUID PRIMARY KEY,
    conversation_id UUID NOT NULL REFERENCES business.conversations(id) ON DELETE CASCADE,
    role VARCHAR(16) NOT NULL,
    content VARCHAR NOT NULL,
    answer_mode VARCHAR(32),
    notice VARCHAR,
    knowledge_base_score DOUBLE PRECISION,
    citations_json VARCHAR NOT NULL DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_chat_messages_conversation_created
    ON business.chat_messages(conversation_id, created_at);

ALTER TABLE business.documents ADD COLUMN chunk_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE business.documents ADD COLUMN image_count INTEGER NOT NULL DEFAULT 0;

CREATE TABLE rag.document_chunks (
    chunk_id VARCHAR(255) PRIMARY KEY,
    document_version_id UUID
);

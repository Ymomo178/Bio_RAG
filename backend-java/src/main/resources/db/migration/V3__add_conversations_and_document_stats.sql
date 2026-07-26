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
    content TEXT NOT NULL,
    answer_mode VARCHAR(32),
    notice TEXT,
    knowledge_base_score DOUBLE PRECISION,
    citations_json TEXT NOT NULL DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_chat_messages_conversation_created
    ON business.chat_messages(conversation_id, created_at);

ALTER TABLE business.documents
    ADD COLUMN chunk_count INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN image_count INTEGER NOT NULL DEFAULT 0;

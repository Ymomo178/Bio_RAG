CREATE SCHEMA IF NOT EXISTS business;

CREATE TABLE business.users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE business.roles (
    id UUID PRIMARY KEY,
    code VARCHAR(32) NOT NULL UNIQUE,
    name VARCHAR(64) NOT NULL
);

CREATE TABLE business.user_roles (
    user_id UUID NOT NULL REFERENCES business.users(id),
    role_id UUID NOT NULL REFERENCES business.roles(id),
    PRIMARY KEY (user_id, role_id)
);

CREATE TABLE business.knowledge_bases (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    owner_id UUID NOT NULL REFERENCES business.users(id),
    visibility VARCHAR(32) NOT NULL DEFAULT 'PRIVATE',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_knowledge_bases_owner ON business.knowledge_bases(owner_id);

CREATE TABLE business.kb_members (
    knowledge_base_id UUID NOT NULL REFERENCES business.knowledge_bases(id),
    user_id UUID NOT NULL REFERENCES business.users(id),
    permission VARCHAR(32) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (knowledge_base_id, user_id)
);

CREATE TABLE business.documents (
    id UUID PRIMARY KEY,
    knowledge_base_id UUID NOT NULL REFERENCES business.knowledge_bases(id),
    name VARCHAR(255) NOT NULL,
    content_type VARCHAR(128) NOT NULL,
    file_hash VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'UPLOADED',
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (knowledge_base_id, file_hash)
);

CREATE INDEX idx_documents_knowledge_base ON business.documents(knowledge_base_id);

CREATE TABLE business.document_versions (
    id UUID PRIMARY KEY,
    document_id UUID NOT NULL REFERENCES business.documents(id),
    version_number INTEGER NOT NULL,
    storage_path VARCHAR(1024) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (document_id, version_number)
);

CREATE TABLE business.index_jobs (
    id UUID PRIMARY KEY,
    document_version_id UUID NOT NULL REFERENCES business.document_versions(id),
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    attempts INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_index_jobs_document_version ON business.index_jobs(document_version_id);

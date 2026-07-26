-- 初始化系统角色，固定 UUID 便于不同环境保持一致。
INSERT INTO business.roles (id, code, name) VALUES
    ('00000000-0000-0000-0000-000000000001', 'USER', '普通用户'),
    ('00000000-0000-0000-0000-000000000002', 'ADMIN', '管理员')
ON CONFLICT (code) DO NOTHING;

-- 已有账号默认补充普通用户角色。
INSERT INTO business.user_roles (user_id, role_id)
SELECT users.id, roles.id
FROM business.users AS users
CROSS JOIN business.roles AS roles
WHERE roles.code = 'USER'
ON CONFLICT DO NOTHING;

-- 会话与知识库改为多对多关系，并保留旧会话的选择。
CREATE TABLE business.conversation_knowledge_bases (
    conversation_id UUID NOT NULL REFERENCES business.conversations(id) ON DELETE CASCADE,
    knowledge_base_id UUID NOT NULL REFERENCES business.knowledge_bases(id) ON DELETE CASCADE,
    PRIMARY KEY (conversation_id, knowledge_base_id)
);

INSERT INTO business.conversation_knowledge_bases (conversation_id, knowledge_base_id)
SELECT id, knowledge_base_id
FROM business.conversations
WHERE knowledge_base_id IS NOT NULL;

ALTER TABLE business.conversations DROP COLUMN knowledge_base_id;

CREATE INDEX idx_conversation_kb_knowledge_base
    ON business.conversation_knowledge_bases(knowledge_base_id);

CREATE INDEX idx_knowledge_bases_visibility
    ON business.knowledge_bases(visibility, created_at DESC);

MERGE INTO business.roles (id, code, name) KEY(code) VALUES
    ('00000000-0000-0000-0000-000000000001', 'USER', '普通用户'),
    ('00000000-0000-0000-0000-000000000002', 'ADMIN', '管理员');

INSERT INTO business.user_roles (user_id, role_id)
SELECT users.id, roles.id
FROM business.users AS users
CROSS JOIN business.roles AS roles
WHERE roles.code = 'USER'
  AND NOT EXISTS (
      SELECT 1 FROM business.user_roles
      WHERE user_roles.user_id = users.id AND user_roles.role_id = roles.id
  );

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

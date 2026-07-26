package com.biorag.platform.chat.dto;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

/**
 * 网页会话列表使用的会话摘要。
 */
public record ConversationResponse(
        UUID id,
        String title,
        UUID knowledgeBaseId,
        String knowledgeBaseName,
        List<UUID> knowledgeBaseIds,
        List<String> knowledgeBaseNames,
        Instant createdAt,
        Instant updatedAt) {
}

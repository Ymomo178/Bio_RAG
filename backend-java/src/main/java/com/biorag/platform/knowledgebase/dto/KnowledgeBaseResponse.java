package com.biorag.platform.knowledgebase.dto;

import com.biorag.platform.knowledgebase.entity.KnowledgeBaseVisibility;
import java.time.Instant;
import java.util.UUID;

/**
 * 知识库接口响应，与数据库实体保持隔离。
 */
public record KnowledgeBaseResponse(
        UUID id,
        String name,
        String description,
        UUID ownerId,
        String ownerEmail,
        KnowledgeBaseVisibility visibility,
        boolean owned,
        boolean editable,
        Instant createdAt,
        Instant updatedAt) {
}

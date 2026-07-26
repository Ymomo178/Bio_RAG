package com.biorag.platform.document.dto;

import com.biorag.platform.document.entity.DocumentStatus;
import java.time.Instant;
import java.util.UUID;

/**
 * 网页文档管理列表使用的响应。
 */
public record DocumentResponse(
        UUID id,
        UUID knowledgeBaseId,
        String name,
        String contentType,
        DocumentStatus status,
        String errorMessage,
        int chunkCount,
        int imageCount,
        Instant createdAt,
        Instant updatedAt) {
}

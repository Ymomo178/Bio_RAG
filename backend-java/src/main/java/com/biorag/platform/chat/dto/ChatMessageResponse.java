package com.biorag.platform.chat.dto;

import com.biorag.platform.integration.ai.AiCitationResponse;
import java.time.Instant;
import java.util.List;
import java.util.UUID;

/**
 * 返回给网页的一条持久化会话消息。
 */
public record ChatMessageResponse(
        UUID id,
        String role,
        String content,
        String answerMode,
        String notice,
        Double knowledgeBaseScore,
        List<AiCitationResponse> citations,
        Instant createdAt) {
}

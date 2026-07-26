package com.biorag.platform.integration.ai;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;
import java.util.UUID;

/**
 * Java 调用 Python 多轮 RAG 问答接口的请求。
 */
public record AiAnswerRequest(
        String question,
        @JsonProperty("top_k") int topK,
        @JsonProperty("knowledge_base_ids") List<UUID> knowledgeBaseIds,
        List<AiHistoryMessage> history) {
}

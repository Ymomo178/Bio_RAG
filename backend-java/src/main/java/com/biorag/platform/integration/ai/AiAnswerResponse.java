package com.biorag.platform.integration.ai;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;

/**
 * Python 返回的完整 RAG 回答。
 */
public record AiAnswerResponse(
        String question,
        @JsonProperty("standalone_question") String standaloneQuestion,
        String answer,
        @JsonProperty("has_evidence") boolean hasEvidence,
        List<AiCitationResponse> citations,
        @JsonProperty("answer_mode") String answerMode,
        String notice,
        @JsonProperty("knowledge_base_score") Double knowledgeBaseScore) {
}

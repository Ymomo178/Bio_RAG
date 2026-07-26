package com.biorag.platform.integration.ai;

import com.fasterxml.jackson.annotation.JsonAlias;
import java.util.List;

/**
 * Python 返回的一条经过验证的知识库引用。
 */
public record AiCitationResponse(
        @JsonAlias("evidence_id") String evidenceId,
        @JsonAlias("chunk_id") String chunkId,
        double score,
        @JsonAlias("source_id") String sourceId,
        @JsonAlias("normalized_path") String normalizedPath,
        String section,
        @JsonAlias("page_number") Integer pageNumber,
        @JsonAlias("image_ids") List<String> imageIds) {
}

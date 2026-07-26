package com.biorag.platform.integration.ai;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.UUID;

/**
 * Python 完成单文档索引后返回的统计结果。
 */
public record AiDocumentIndexResponse(
        @JsonProperty("document_version_id") UUID documentVersionId,
        @JsonProperty("chunk_count") int chunkCount,
        @JsonProperty("image_count") int imageCount,
        @JsonProperty("document_title") String documentTitle) {
}

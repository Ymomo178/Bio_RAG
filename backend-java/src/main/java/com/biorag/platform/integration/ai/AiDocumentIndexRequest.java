package com.biorag.platform.integration.ai;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.UUID;

/**
 * Java 通知 Python 处理已保存上传文件的请求。
 */
public record AiDocumentIndexRequest(
        @JsonProperty("knowledge_base_id") UUID knowledgeBaseId,
        @JsonProperty("document_version_id") UUID documentVersionId,
        @JsonProperty("source_path") String sourcePath,
        @JsonProperty("original_filename") String originalFilename) {
}

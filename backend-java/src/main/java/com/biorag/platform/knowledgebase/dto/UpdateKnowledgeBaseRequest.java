package com.biorag.platform.knowledgebase.dto;

import com.biorag.platform.knowledgebase.entity.KnowledgeBaseVisibility;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

/**
 * 修改知识库请求，首版使用完整更新语义。
 */
public record UpdateKnowledgeBaseRequest(
        @NotBlank(message = "知识库名称不能为空")
        @Size(max = 255, message = "知识库名称不能超过 255 个字符")
        String name,

        @Size(max = 2000, message = "知识库描述不能超过 2000 个字符")
        String description,

        @NotNull(message = "知识库可见范围不能为空")
        KnowledgeBaseVisibility visibility) {

    /**
     * 清理名称和描述中的首尾空格。
     */
    public UpdateKnowledgeBaseRequest {
        name = name == null ? null : name.trim();
        if (description == null || description.isBlank()) {
            description = null;
        } else {
            description = description.trim();
        }
    }
}

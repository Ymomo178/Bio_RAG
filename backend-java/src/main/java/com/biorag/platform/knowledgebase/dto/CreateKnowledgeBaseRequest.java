package com.biorag.platform.knowledgebase.dto;

import com.biorag.platform.knowledgebase.entity.KnowledgeBaseVisibility;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/**
 * 创建知识库请求，所有者由 Session 决定，客户端不能指定。
 */
public record CreateKnowledgeBaseRequest(
        @NotBlank(message = "知识库名称不能为空")
        @Size(max = 255, message = "知识库名称不能超过 255 个字符")
        String name,

        @Size(max = 2000, message = "知识库描述不能超过 2000 个字符")
        String description,

        KnowledgeBaseVisibility visibility) {

    /**
     * 清理文本输入，并在未指定时使用私有可见范围。
     */
    public CreateKnowledgeBaseRequest {
        name = normalizeRequiredText(name);
        description = normalizeOptionalText(description);
        if (visibility == null) {
            visibility = KnowledgeBaseVisibility.PRIVATE;
        }
    }

    /**
     * 去除必填文本首尾空格，空值留给 Validation 处理。
     */
    private static String normalizeRequiredText(String value) {
        return value == null ? null : value.trim();
    }

    /**
     * 去除可选文本首尾空格，并把空字符串统一为 null。
     */
    private static String normalizeOptionalText(String value) {
        if (value == null || value.isBlank()) {
            return null;
        }
        return value.trim();
    }
}

package com.biorag.platform.chat.dto;

import jakarta.validation.constraints.Size;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.UUID;

/**
 * 创建会话时可选择标题和知识库范围。
 */
public record CreateConversationRequest(
        @Size(max = 255, message = "标题不能超过 255 个字符") String title,
        @Size(max = 20, message = "一次最多选择 20 个知识库") List<UUID> knowledgeBaseIds,
        UUID knowledgeBaseId) {

    /** 兼容首版 Java 调用方的单知识库构造方式。 */
    public CreateConversationRequest(String title, UUID knowledgeBaseId) {
        this(title, List.of(), knowledgeBaseId);
    }

    /** 合并新旧请求字段并去重。 */
    public List<UUID> resolvedKnowledgeBaseIds() {
        LinkedHashSet<UUID> ids = new LinkedHashSet<>();
        if (knowledgeBaseIds != null) {
            ids.addAll(knowledgeBaseIds);
        }
        if (knowledgeBaseId != null) {
            ids.add(knowledgeBaseId);
        }
        return List.copyOf(ids);
    }
}

package com.biorag.platform.knowledgebase.exception;

import java.util.UUID;

/**
 * 指定知识库不存在时抛出的业务异常。
 */
public class KnowledgeBaseNotFoundException extends RuntimeException {

    /**
     * 使用未找到的知识库 ID 创建异常。
     */
    public KnowledgeBaseNotFoundException(UUID knowledgeBaseId) {
        super("知识库不存在：" + knowledgeBaseId);
    }
}

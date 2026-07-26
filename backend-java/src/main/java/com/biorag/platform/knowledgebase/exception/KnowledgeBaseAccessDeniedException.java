package com.biorag.platform.knowledgebase.exception;

/**
 * 当前用户不是知识库所有者却尝试执行所有者操作时抛出的异常。
 */
public class KnowledgeBaseAccessDeniedException extends RuntimeException {

    /**
     * 使用固定的无权访问提示创建异常。
     */
    public KnowledgeBaseAccessDeniedException() {
        super("无权操作该知识库");
    }
}

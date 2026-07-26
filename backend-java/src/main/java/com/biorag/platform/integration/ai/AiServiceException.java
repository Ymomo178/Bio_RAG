package com.biorag.platform.integration.ai;

/**
 * 表示 Java 无法从 Python AI 服务获得有效结果。
 */
public class AiServiceException extends RuntimeException {

    /**
     * 使用便于用户理解的信息创建 AI 服务异常。
     */
    public AiServiceException(String message, Throwable cause) {
        super(message, cause);
    }
}

package com.biorag.platform.chat.exception;

import java.util.UUID;

/**
 * 当前用户无法找到指定会话时抛出的异常。
 */
public class ConversationNotFoundException extends RuntimeException {

    /** 使用会话 ID 创建不暴露其他用户数据的错误。 */
    public ConversationNotFoundException(UUID conversationId) {
        super("会话不存在或无权访问：" + conversationId);
    }
}

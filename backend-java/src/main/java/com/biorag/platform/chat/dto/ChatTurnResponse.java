package com.biorag.platform.chat.dto;

/**
 * 一次问答完成后返回用户消息和助手消息。
 */
public record ChatTurnResponse(
        ConversationResponse conversation,
        ChatMessageResponse userMessage,
        ChatMessageResponse assistantMessage,
        String standaloneQuestion) {
}

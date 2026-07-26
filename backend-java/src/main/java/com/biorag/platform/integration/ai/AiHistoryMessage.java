package com.biorag.platform.integration.ai;

import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * 发送给 Python 的一条最近会话消息。
 */
public record AiHistoryMessage(String role, String content) {
}

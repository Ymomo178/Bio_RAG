package com.biorag.platform.chat.repository;

import com.biorag.platform.chat.entity.ChatMessage;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

/**
 * 会话消息数据访问接口。
 */
public interface ChatMessageRepository extends JpaRepository<ChatMessage, UUID> {

    /** 按时间正序加载完整会话记录。 */
    List<ChatMessage> findAllByConversation_IdOrderByCreatedAtAsc(UUID conversationId);

    /** 加载最近十二条消息，用于构建有限的模型记忆。 */
    List<ChatMessage> findTop12ByConversation_IdOrderByCreatedAtDesc(UUID conversationId);
}

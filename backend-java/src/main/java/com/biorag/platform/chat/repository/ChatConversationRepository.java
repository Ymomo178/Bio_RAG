package com.biorag.platform.chat.repository;

import com.biorag.platform.chat.entity.ChatConversation;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

/**
 * 会话数据访问接口。
 */
public interface ChatConversationRepository extends JpaRepository<ChatConversation, UUID> {

    /** 查询当前用户的会话，并按最近活跃时间倒序排列。 */
    List<ChatConversation> findAllByOwner_IdOrderByUpdatedAtDesc(UUID ownerId);

    /** 按会话 ID 和所有者同时查询，避免跨用户读取。 */
    Optional<ChatConversation> findByIdAndOwner_Id(UUID id, UUID ownerId);
}

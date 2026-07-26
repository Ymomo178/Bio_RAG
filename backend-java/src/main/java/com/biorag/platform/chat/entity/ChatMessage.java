package com.biorag.platform.chat.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.PrePersist;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.Objects;
import java.util.UUID;

/**
 * 会话消息实体，保存用户问题、AI 回答和引用快照。
 */
@Entity
@Table(name = "chat_messages", schema = "business")
public class ChatMessage {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "conversation_id", nullable = false)
    private ChatConversation conversation;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 16)
    private MessageRole role;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String content;

    @Column(name = "answer_mode", length = 32)
    private String answerMode;

    @Column(columnDefinition = "TEXT")
    private String notice;

    @Column(name = "knowledge_base_score")
    private Double knowledgeBaseScore;

    @Column(name = "citations_json", nullable = false, columnDefinition = "TEXT")
    private String citationsJson;

    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt;

    /** 供 JPA 还原数据库记录。 */
    protected ChatMessage() {
    }

    /** 创建一条用户消息。 */
    public static ChatMessage user(ChatConversation conversation, String content) {
        return new ChatMessage(conversation, MessageRole.USER, content, null, null, null, "[]");
    }

    /** 创建一条带回答模式和引用快照的助手消息。 */
    public static ChatMessage assistant(
            ChatConversation conversation,
            String content,
            String answerMode,
            String notice,
            Double knowledgeBaseScore,
            String citationsJson) {
        return new ChatMessage(
                conversation,
                MessageRole.ASSISTANT,
                content,
                answerMode,
                notice,
                knowledgeBaseScore,
                citationsJson);
    }

    /** 初始化一条完整会话消息。 */
    private ChatMessage(
            ChatConversation conversation,
            MessageRole role,
            String content,
            String answerMode,
            String notice,
            Double knowledgeBaseScore,
            String citationsJson) {
        this.conversation = Objects.requireNonNull(conversation, "conversation must not be null");
        this.role = Objects.requireNonNull(role, "role must not be null");
        this.content = Objects.requireNonNull(content, "content must not be null");
        this.answerMode = answerMode;
        this.notice = notice;
        this.knowledgeBaseScore = knowledgeBaseScore;
        this.citationsJson = Objects.requireNonNull(citationsJson, "citationsJson must not be null");
    }

    /** 首次保存时记录消息时间。 */
    @PrePersist
    void beforeInsert() {
        createdAt = Instant.now();
    }

    /** 返回消息 ID。 */
    public UUID getId() {
        return id;
    }

    /** 返回所属会话。 */
    public ChatConversation getConversation() {
        return conversation;
    }

    /** 返回消息角色。 */
    public MessageRole getRole() {
        return role;
    }

    /** 返回消息正文。 */
    public String getContent() {
        return content;
    }

    /** 返回助手回答模式。 */
    public String getAnswerMode() {
        return answerMode;
    }

    /** 返回回答来源提示。 */
    public String getNotice() {
        return notice;
    }

    /** 返回知识库最高证据分数。 */
    public Double getKnowledgeBaseScore() {
        return knowledgeBaseScore;
    }

    /** 返回序列化后的引用快照。 */
    public String getCitationsJson() {
        return citationsJson;
    }

    /** 返回消息创建时间。 */
    public Instant getCreatedAt() {
        return createdAt;
    }
}

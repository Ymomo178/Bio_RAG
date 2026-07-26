package com.biorag.platform.chat.entity;

import com.biorag.platform.auth.entity.UserAccount;
import com.biorag.platform.knowledgebase.entity.KnowledgeBase;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.JoinTable;
import jakarta.persistence.ManyToMany;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.PrePersist;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.LinkedHashSet;
import java.util.Objects;
import java.util.Set;
import java.util.UUID;

/**
 * 会话实体，保存用户、知识库范围和会话标题。
 */
@Entity
@Table(name = "conversations", schema = "business")
public class ChatConversation {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "owner_id", nullable = false)
    private UserAccount owner;

    @ManyToMany(fetch = FetchType.LAZY)
    @JoinTable(
            name = "conversation_knowledge_bases",
            schema = "business",
            joinColumns = @JoinColumn(name = "conversation_id"),
            inverseJoinColumns = @JoinColumn(name = "knowledge_base_id"))
    private Set<KnowledgeBase> knowledgeBases = new LinkedHashSet<>();

    @Column(nullable = false, length = 255)
    private String title;

    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt;

    /** 供 JPA 还原数据库记录。 */
    protected ChatConversation() {
    }

    /** 创建一个属于当前用户的新会话。 */
    public ChatConversation(UserAccount owner, Set<KnowledgeBase> knowledgeBases, String title) {
        this.owner = Objects.requireNonNull(owner, "owner must not be null");
        this.knowledgeBases.addAll(Objects.requireNonNull(knowledgeBases, "knowledgeBases must not be null"));
        this.title = Objects.requireNonNull(title, "title must not be null");
    }

    /** 使用第一条问题替换默认标题，并刷新会话排序时间。 */
    public void acceptUserQuestion(String question) {
        if ("新对话".equals(title)) {
            String compact = question.strip().replaceAll("\\s+", " ");
            title = compact.substring(0, Math.min(compact.length(), 40));
        }
        updatedAt = Instant.now();
    }

    /** 首次保存时初始化创建时间和更新时间。 */
    @PrePersist
    void beforeInsert() {
        Instant now = Instant.now();
        createdAt = now;
        updatedAt = now;
    }

    /** 返回会话 ID。 */
    public UUID getId() {
        return id;
    }

    /** 返回会话所有者。 */
    public UserAccount getOwner() {
        return owner;
    }

    /** 返回当前会话使用的知识库集合，空集合表示旧版内置资料。 */
    public Set<KnowledgeBase> getKnowledgeBases() {
        return Set.copyOf(knowledgeBases);
    }

    /** 返回会话标题。 */
    public String getTitle() {
        return title;
    }

    /** 返回会话创建时间。 */
    public Instant getCreatedAt() {
        return createdAt;
    }

    /** 返回会话最后活跃时间。 */
    public Instant getUpdatedAt() {
        return updatedAt;
    }
}

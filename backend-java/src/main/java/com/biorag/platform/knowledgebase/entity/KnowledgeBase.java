package com.biorag.platform.knowledgebase.entity;

import com.biorag.platform.auth.entity.UserAccount;
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
import jakarta.persistence.PreUpdate;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.Objects;
import java.util.UUID;

/**
 * 知识库实体，表示一组可被 RAG 检索的文档集合。
 */
@Entity
@Table(name = "knowledge_bases", schema = "business")
public class KnowledgeBase {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(nullable = false, length = 255)
    private String name;

    @Column
    private String description;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "owner_id", nullable = false)
    private UserAccount owner;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 32)
    private KnowledgeBaseVisibility visibility;

    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt;

    /**
     * 供 JPA 从数据库记录还原对象时使用。
     */
    protected KnowledgeBase() {
    }

    /**
     * 创建一个属于指定用户的新知识库。
     */
    public KnowledgeBase(
            String name,
            String description,
            UserAccount owner,
            KnowledgeBaseVisibility visibility) {
        this.name = Objects.requireNonNull(name, "name must not be null");
        this.description = description;
        this.owner = Objects.requireNonNull(owner, "owner must not be null");
        this.visibility = Objects.requireNonNull(visibility, "visibility must not be null");
    }

    /**
     * 修改知识库的可编辑基本信息。
     */
    public void update(String name, String description, KnowledgeBaseVisibility visibility) {
        this.name = Objects.requireNonNull(name, "name must not be null");
        this.description = description;
        this.visibility = Objects.requireNonNull(visibility, "visibility must not be null");
    }

    /**
     * 首次保存前写入创建时间和更新时间。
     */
    @PrePersist
    void beforeInsert() {
        Instant now = Instant.now();
        createdAt = now;
        updatedAt = now;
    }

    /**
     * 数据更新前刷新更新时间。
     */
    @PreUpdate
    void beforeUpdate() {
        updatedAt = Instant.now();
    }

    /** 返回知识库唯一标识。 */
    public UUID getId() {
        return id;
    }

    /** 返回知识库名称。 */
    public String getName() {
        return name;
    }

    /** 返回知识库描述。 */
    public String getDescription() {
        return description;
    }

    /** 返回知识库所有者。 */
    public UserAccount getOwner() {
        return owner;
    }

    /** 返回知识库可见范围。 */
    public KnowledgeBaseVisibility getVisibility() {
        return visibility;
    }

    /** 返回知识库创建时间。 */
    public Instant getCreatedAt() {
        return createdAt;
    }

    /** 返回知识库最后更新时间。 */
    public Instant getUpdatedAt() {
        return updatedAt;
    }
}

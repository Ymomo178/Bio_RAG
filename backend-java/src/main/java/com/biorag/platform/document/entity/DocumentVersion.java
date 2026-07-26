package com.biorag.platform.document.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
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
 * 文档版本实体，记录原文件在本机上传目录中的位置。
 */
@Entity
@Table(name = "document_versions", schema = "business")
public class DocumentVersion {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "document_id", nullable = false)
    private KnowledgeDocument document;

    @Column(name = "version_number", nullable = false)
    private int versionNumber;

    @Column(name = "storage_path", nullable = false, length = 1024)
    private String storagePath;

    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt;

    /** 供 JPA 从数据库还原版本记录。 */
    protected DocumentVersion() {
    }

    /** 创建文档的首个或后续原文件版本。 */
    public DocumentVersion(KnowledgeDocument document, int versionNumber, String storagePath) {
        this.document = Objects.requireNonNull(document, "document must not be null");
        this.versionNumber = versionNumber;
        this.storagePath = Objects.requireNonNull(storagePath, "storagePath must not be null");
    }

    /** 保存前记录版本创建时间。 */
    @PrePersist
    void beforeInsert() {
        createdAt = Instant.now();
    }

    /** 返回文档版本 ID。 */
    public UUID getId() {
        return id;
    }

    /** 返回所属文档。 */
    public KnowledgeDocument getDocument() {
        return document;
    }

    /** 返回版本号。 */
    public int getVersionNumber() {
        return versionNumber;
    }

    /** 返回原文件绝对存储路径。 */
    public String getStoragePath() {
        return storagePath;
    }

    /** 返回版本创建时间。 */
    public Instant getCreatedAt() {
        return createdAt;
    }
}

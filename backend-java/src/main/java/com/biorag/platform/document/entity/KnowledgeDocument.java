package com.biorag.platform.document.entity;

import com.biorag.platform.knowledgebase.entity.KnowledgeBase;
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
 * 用户知识库中的原始文档记录。
 */
@Entity
@Table(name = "documents", schema = "business")
public class KnowledgeDocument {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "knowledge_base_id", nullable = false)
    private KnowledgeBase knowledgeBase;

    @Column(nullable = false, length = 255)
    private String name;

    @Column(name = "content_type", nullable = false, length = 128)
    private String contentType;

    @Column(name = "file_hash", nullable = false, length = 64)
    private String fileHash;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 32)
    private DocumentStatus status;

    @Column(name = "error_message", columnDefinition = "TEXT")
    private String errorMessage;

    @Column(name = "chunk_count", nullable = false)
    private int chunkCount;

    @Column(name = "image_count", nullable = false)
    private int imageCount;

    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt;

    /** 供 JPA 从数据库还原文档记录。 */
    protected KnowledgeDocument() {
    }

    /** 创建一条等待保存和索引的上传文档。 */
    public KnowledgeDocument(
            KnowledgeBase knowledgeBase,
            String name,
            String contentType,
            String fileHash) {
        this.knowledgeBase = Objects.requireNonNull(knowledgeBase, "knowledgeBase must not be null");
        this.name = Objects.requireNonNull(name, "name must not be null");
        this.contentType = Objects.requireNonNull(contentType, "contentType must not be null");
        this.fileHash = Objects.requireNonNull(fileHash, "fileHash must not be null");
        this.status = DocumentStatus.UPLOADED;
    }

    /** 标记文档正在由 Python 解析和建立索引。 */
    public void markIndexing() {
        status = DocumentStatus.INDEXING;
        errorMessage = null;
    }

    /** 保存文档成功生成的文本块和图片数量。 */
    public void markReady(int chunkCount, int imageCount) {
        status = DocumentStatus.READY;
        errorMessage = null;
        this.chunkCount = chunkCount;
        this.imageCount = imageCount;
    }

    /** 保存索引失败原因，便于网页显示和后续重试。 */
    public void markFailed(String message) {
        status = DocumentStatus.FAILED;
        errorMessage = message == null ? "未知索引错误" : message.substring(0, Math.min(message.length(), 2000));
    }

    /** 首次保存时初始化时间字段。 */
    @PrePersist
    void beforeInsert() {
        Instant now = Instant.now();
        createdAt = now;
        updatedAt = now;
    }

    /** 状态变化时刷新更新时间。 */
    @PreUpdate
    void beforeUpdate() {
        updatedAt = Instant.now();
    }

    /** 返回文档 ID。 */
    public UUID getId() {
        return id;
    }

    /** 返回所属知识库。 */
    public KnowledgeBase getKnowledgeBase() {
        return knowledgeBase;
    }

    /** 返回原始文件名。 */
    public String getName() {
        return name;
    }

    /** 返回 MIME 类型。 */
    public String getContentType() {
        return contentType;
    }

    /** 返回文件内容哈希。 */
    public String getFileHash() {
        return fileHash;
    }

    /** 返回文档处理状态。 */
    public DocumentStatus getStatus() {
        return status;
    }

    /** 返回索引失败原因。 */
    public String getErrorMessage() {
        return errorMessage;
    }

    /** 返回生成的文本块数量。 */
    public int getChunkCount() {
        return chunkCount;
    }

    /** 返回提取的图片数量。 */
    public int getImageCount() {
        return imageCount;
    }

    /** 返回创建时间。 */
    public Instant getCreatedAt() {
        return createdAt;
    }

    /** 返回更新时间。 */
    public Instant getUpdatedAt() {
        return updatedAt;
    }
}

package com.biorag.platform.document.service;

import com.biorag.platform.document.dto.DocumentResponse;
import com.biorag.platform.document.entity.DocumentVersion;
import com.biorag.platform.document.entity.KnowledgeDocument;
import com.biorag.platform.document.exception.DocumentNotFoundException;
import com.biorag.platform.document.exception.DuplicateDocumentException;
import com.biorag.platform.document.exception.UnsupportedDocumentException;
import com.biorag.platform.document.repository.DocumentVersionRepository;
import com.biorag.platform.document.repository.KnowledgeDocumentRepository;
import com.biorag.platform.integration.ai.AiDocumentIndexRequest;
import com.biorag.platform.integration.ai.AiDocumentIndexResponse;
import com.biorag.platform.integration.ai.AiServiceClient;
import com.biorag.platform.knowledgebase.entity.KnowledgeBase;
import com.biorag.platform.knowledgebase.service.KnowledgeBaseService;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Path;
import java.security.DigestInputStream;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionTemplate;
import org.springframework.web.multipart.MultipartFile;

/**
 * 文档业务服务，串联权限、原文件存储、Python 索引和状态记录。
 */
@Service
public class DocumentService {

    private static final Logger log = LoggerFactory.getLogger(DocumentService.class);
    private static final Set<String> SUPPORTED_EXTENSIONS = Set.of(
            "pdf", "docx", "html", "htm", "md", "mdx", "rst", "txt");

    private final KnowledgeDocumentRepository documentRepository;
    private final DocumentVersionRepository versionRepository;
    private final KnowledgeBaseService knowledgeBaseService;
    private final DocumentStorageService storageService;
    private final AiServiceClient aiServiceClient;
    private final JdbcTemplate jdbcTemplate;
    private final TransactionTemplate transactionTemplate;

    /** 注入文档持久化、存储、权限和 AI 处理依赖。 */
    public DocumentService(
            KnowledgeDocumentRepository documentRepository,
            DocumentVersionRepository versionRepository,
            KnowledgeBaseService knowledgeBaseService,
            DocumentStorageService storageService,
            AiServiceClient aiServiceClient,
            JdbcTemplate jdbcTemplate,
            TransactionTemplate transactionTemplate) {
        this.documentRepository = documentRepository;
        this.versionRepository = versionRepository;
        this.knowledgeBaseService = knowledgeBaseService;
        this.storageService = storageService;
        this.aiServiceClient = aiServiceClient;
        this.jdbcTemplate = jdbcTemplate;
        this.transactionTemplate = transactionTemplate;
    }

    /** 保存并同步索引一份属于当前用户知识库的文档。 */
    public DocumentResponse upload(
            UUID currentUserId,
            UUID knowledgeBaseId,
            MultipartFile file) {
        validateFile(file);
        KnowledgeBase knowledgeBase = knowledgeBaseService.requireOwnedEntity(
                currentUserId,
                knowledgeBaseId);
        String hash = sha256(file);
        if (documentRepository.existsByKnowledgeBase_IdAndFileHash(knowledgeBaseId, hash)) {
            throw new DuplicateDocumentException();
        }
        String filename = Path.of(file.getOriginalFilename()).getFileName().toString();
        String contentType = file.getContentType() == null
                ? "application/octet-stream"
                : file.getContentType();
        KnowledgeDocument document = documentRepository.saveAndFlush(
                new KnowledgeDocument(knowledgeBase, filename, contentType, hash));
        DocumentVersion version = versionRepository.saveAndFlush(
                new DocumentVersion(document, 1, "PENDING"));
        Path storagePath = storageService.store(
                file,
                currentUserId,
                knowledgeBaseId,
                document.getId(),
                version.getId());
        jdbcTemplate.update(
                "UPDATE business.document_versions SET storage_path = ? WHERE id = ?",
                storagePath.toString(),
                version.getId());
        document.markIndexing();
        documentRepository.saveAndFlush(document);
        try {
            AiDocumentIndexResponse indexed = aiServiceClient.indexDocument(
                    new AiDocumentIndexRequest(
                            knowledgeBaseId,
                            version.getId(),
                            storagePath.toString(),
                            filename));
            document.markReady(indexed.chunkCount(), indexed.imageCount());
        } catch (RuntimeException exception) {
            document.markFailed(exception.getMessage());
        }
        return toResponse(documentRepository.saveAndFlush(document));
    }

    /** 查询当前用户指定知识库中的全部文档。 */
    @Transactional(readOnly = true)
    public List<DocumentResponse> list(UUID currentUserId, UUID knowledgeBaseId) {
        knowledgeBaseService.requireAccessibleEntity(currentUserId, knowledgeBaseId);
        return documentRepository.findAllByKnowledgeBase_IdOrderByCreatedAtDesc(knowledgeBaseId).stream()
                .map(this::toResponse)
                .toList();
    }

    /** 删除文档记录、版本和对应的向量文本块。 */
    public void delete(UUID currentUserId, UUID documentId) {
        KnowledgeDocument document = documentRepository.findById(documentId)
                .orElseThrow(() -> new DocumentNotFoundException(documentId));
        knowledgeBaseService.requireOwnedEntity(currentUserId, document.getKnowledgeBase().getId());
        List<DocumentVersion> versions = versionRepository.findAllByDocument_Id(documentId);
        List<Path> storedFiles = versions.stream()
                .map(version -> Path.of(version.getStoragePath()))
                .toList();
        transactionTemplate.executeWithoutResult(status -> {
            jdbcTemplate.update(
                    "DELETE FROM rag.document_chunks WHERE document_version_id IN "
                            + "(SELECT id FROM business.document_versions WHERE document_id = ?)",
                    documentId);
            jdbcTemplate.update(
                    "DELETE FROM business.index_jobs WHERE document_version_id IN "
                            + "(SELECT id FROM business.document_versions WHERE document_id = ?)",
                    documentId);
            jdbcTemplate.update("DELETE FROM business.document_versions WHERE document_id = ?", documentId);
            jdbcTemplate.update("DELETE FROM business.documents WHERE id = ?", documentId);
        });
        for (int index = 0; index < versions.size(); index++) {
            try {
                storageService.delete(storedFiles.get(index));
                storageService.deleteArtifacts(versions.get(index).getId());
            } catch (RuntimeException exception) {
                log.warn("文档数据库记录已删除，但本地文件清理失败：{}", documentId, exception);
            }
        }
    }

    /** 校验文件非空且扩展名属于当前解析器支持范围。 */
    private void validateFile(MultipartFile file) {
        if (file == null || file.isEmpty() || file.getOriginalFilename() == null) {
            throw new UnsupportedDocumentException("请选择一个非空文档");
        }
        String name = file.getOriginalFilename();
        int dot = name.lastIndexOf('.');
        String extension = dot < 0 ? "" : name.substring(dot + 1).toLowerCase(Locale.ROOT);
        if (!SUPPORTED_EXTENSIONS.contains(extension)) {
            throw new UnsupportedDocumentException(
                    "暂不支持该格式，可上传 PDF、DOCX、HTML、MD、RST 或 TXT");
        }
    }

    /** 流式计算文件 SHA-256，避免将整个文件读入内存。 */
    private String sha256(MultipartFile file) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            try (InputStream input = file.getInputStream();
                    DigestInputStream digestInput = new DigestInputStream(input, digest)) {
                digestInput.transferTo(java.io.OutputStream.nullOutputStream());
            }
            return HexFormat.of().formatHex(digest.digest()).toUpperCase(Locale.ROOT);
        } catch (IOException | NoSuchAlgorithmException exception) {
            throw new IllegalStateException("无法计算上传文件哈希", exception);
        }
    }

    /** 将文档实体转换为网页管理响应。 */
    private DocumentResponse toResponse(KnowledgeDocument document) {
        return new DocumentResponse(
                document.getId(),
                document.getKnowledgeBase().getId(),
                document.getName(),
                document.getContentType(),
                document.getStatus(),
                document.getErrorMessage(),
                document.getChunkCount(),
                document.getImageCount(),
                document.getCreatedAt(),
                document.getUpdatedAt());
    }
}

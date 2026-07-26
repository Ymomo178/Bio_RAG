package com.biorag.platform.document.service;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.Comparator;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

/**
 * 负责把上传原文件保存到受控的本机目录。
 */
@Service
public class DocumentStorageService {

    private final Path uploadRoot;
    private final Path artifactRoot;

    /** 读取并规范化统一上传根目录。 */
    public DocumentStorageService(
            @Value("${app.storage.root}") String uploadRoot,
            @Value("${app.storage.artifact-root}") String artifactRoot) {
        this.uploadRoot = Path.of(uploadRoot).toAbsolutePath().normalize();
        this.artifactRoot = Path.of(artifactRoot).toAbsolutePath().normalize();
    }

    /** 按用户、知识库、文档和版本分层保存原文件。 */
    public Path store(
            MultipartFile file,
            UUID userId,
            UUID knowledgeBaseId,
            UUID documentId,
            UUID versionId) {
        String safeName = sanitizeFilename(file.getOriginalFilename());
        Path targetDirectory = uploadRoot
                .resolve(userId.toString())
                .resolve(knowledgeBaseId.toString())
                .resolve(documentId.toString())
                .resolve(versionId.toString())
                .normalize();
        if (!targetDirectory.startsWith(uploadRoot)) {
            throw new IllegalStateException("上传路径超出允许目录");
        }
        Path target = targetDirectory.resolve(safeName).normalize();
        try {
            Files.createDirectories(targetDirectory);
            try (var input = file.getInputStream()) {
                Files.copy(input, target, StandardCopyOption.REPLACE_EXISTING);
            }
            return target.toAbsolutePath();
        } catch (IOException exception) {
            throw new IllegalStateException("无法保存上传文件", exception);
        }
    }

    /** 删除统一上传目录中的一个已登记原文件。 */
    public void delete(Path storedFile) {
        Path normalized = storedFile.toAbsolutePath().normalize();
        if (!normalized.startsWith(uploadRoot)) {
            throw new IllegalStateException("拒绝删除上传目录外的文件");
        }
        try {
            Files.deleteIfExists(normalized);
        } catch (IOException exception) {
            throw new IllegalStateException("无法删除上传原文件", exception);
        }
    }

    /** 删除 Python 为指定文档版本生成的 Markdown 和图片资产。 */
    public void deleteArtifacts(UUID documentVersionId) {
        Path versionDirectory = artifactRoot.resolve(documentVersionId.toString()).normalize();
        if (!versionDirectory.startsWith(artifactRoot) || versionDirectory.equals(artifactRoot)) {
            throw new IllegalStateException("拒绝删除索引资产根目录");
        }
        if (!Files.exists(versionDirectory)) {
            return;
        }
        try (var paths = Files.walk(versionDirectory)) {
            for (Path path : paths.sorted(Comparator.reverseOrder()).toList()) {
                Files.deleteIfExists(path);
            }
        } catch (IOException exception) {
            throw new IllegalStateException("无法删除文档索引资产", exception);
        }
    }

    /** 只保留文件名并替换不适合本机路径的字符。 */
    private String sanitizeFilename(String originalFilename) {
        String fallback = originalFilename == null || originalFilename.isBlank()
                ? "document.bin"
                : Path.of(originalFilename).getFileName().toString();
        return fallback.replaceAll("[\\\\/:*?\"<>|]", "_");
    }
}

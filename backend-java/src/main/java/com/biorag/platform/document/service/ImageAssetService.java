package com.biorag.platform.document.service;

import com.biorag.platform.knowledgebase.service.KnowledgeBaseService;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

/** 定位检索引用中的原始图片，并在返回前验证知识库权限。 */
@Service
public class ImageAssetService {
    private final JdbcTemplate jdbc;
    private final KnowledgeBaseService knowledgeBases;
    private final ObjectMapper mapper;
    private final Path artifactRoot;
    private final Path repositoryRoot;

    /** 注入数据库、权限服务和受控资源目录。 */
    public ImageAssetService(JdbcTemplate jdbc, KnowledgeBaseService knowledgeBases, ObjectMapper mapper,
            @Value("${app.storage.artifact-root}") String artifactRoot,
            @Value("${app.storage.repository-root:..}") String repositoryRoot) {
        this.jdbc = jdbc;
        this.knowledgeBases = knowledgeBases;
        this.mapper = mapper;
        this.artifactRoot = Path.of(artifactRoot).toAbsolutePath().normalize();
        this.repositoryRoot = Path.of(repositoryRoot).toAbsolutePath().normalize();
    }

    /** 返回有权访问的图片文件。 */
    public ImageAsset find(UUID currentUserId, String imageId) {
        if (!imageId.matches("[A-Za-z0-9._-]+")) throw new IllegalArgumentException("图片 ID 不合法");
        List<Map<String, Object>> rows = jdbc.queryForList(
                "SELECT document_version_id, knowledge_base_id FROM rag.document_chunks "
                        + "WHERE CAST(image_ids AS VARCHAR) LIKE ? LIMIT 1", "%\"" + imageId + "\"%");
        if (rows.isEmpty()) throw new IllegalArgumentException("图片不存在");
        Object knowledgeBaseId = rows.getFirst().get("knowledge_base_id");
        if (knowledgeBaseId != null) knowledgeBases.requireAccessibleEntity(currentUserId, UUID.fromString(knowledgeBaseId.toString()));
        Object versionId = rows.getFirst().get("document_version_id");
        Path path = versionId == null ? findBuiltIn(imageId) : findUploaded(UUID.fromString(versionId.toString()), imageId);
        if (path == null || !Files.isRegularFile(path)) throw new IllegalArgumentException("图片文件不存在");
        try {
            return new ImageAsset(path, Files.probeContentType(path));
        } catch (IOException exception) {
            throw new IllegalStateException("无法读取图片类型", exception);
        }
    }

    /** 在上传文档的资源目录中按 ID 查找图片。 */
    private Path findUploaded(UUID versionId, String imageId) {
        Path directory = artifactRoot.resolve(versionId.toString()).resolve("assets").normalize();
        if (!directory.startsWith(artifactRoot) || !Files.isDirectory(directory)) return null;
        try (var files = Files.list(directory)) {
            return files.filter(path -> path.getFileName().toString().startsWith(imageId + ".")).findFirst().orElse(null);
        } catch (IOException exception) {
            return null;
        }
    }

    /** 从规范化图片清单中定位旧版内置资料图片。 */
    private Path findBuiltIn(String imageId) {
        Path manifest = repositoryRoot.resolve("data/normalized/image-manifest.json").normalize();
        try {
            JsonNode images = mapper.readTree(manifest.toFile()).path("images");
            for (JsonNode image : images) {
                if (imageId.equals(image.path("image_id").asText()) && image.hasNonNull("asset_path")) {
                    Path path = repositoryRoot.resolve(image.path("asset_path").asText()).normalize();
                    return path.startsWith(repositoryRoot) ? path : null;
                }
            }
        } catch (IOException ignored) {
            return null;
        }
        return null;
    }

    /** 图片文件及其媒体类型。 */
    public record ImageAsset(Path path, String contentType) { }
}

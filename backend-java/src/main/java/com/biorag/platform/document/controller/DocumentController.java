package com.biorag.platform.document.controller;

import com.biorag.platform.auth.service.SessionAuthenticationService;
import com.biorag.platform.common.dto.ApiResponse;
import com.biorag.platform.document.dto.DocumentResponse;
import com.biorag.platform.document.service.DocumentService;
import jakarta.servlet.http.HttpSession;
import java.util.List;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

/**
 * 文档管理接口控制器，负责列表、上传和删除。
 */
@RestController
@RequestMapping("/api/knowledge-bases/{knowledgeBaseId}/documents")
public class DocumentController {

    private final DocumentService documentService;
    private final SessionAuthenticationService authenticationService;

    /** 注入文档业务和 Session 认证服务。 */
    public DocumentController(
            DocumentService documentService,
            SessionAuthenticationService authenticationService) {
        this.documentService = documentService;
        this.authenticationService = authenticationService;
    }

    /** 返回指定知识库的文档列表。 */
    @GetMapping
    ApiResponse<List<DocumentResponse>> list(
            @PathVariable UUID knowledgeBaseId,
            HttpSession session) {
        UUID userId = authenticationService.requireUserId(session);
        return ApiResponse.success(documentService.list(userId, knowledgeBaseId));
    }

    /** 接收一个常见格式文件并同步建立向量索引。 */
    @PostMapping(consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    ResponseEntity<ApiResponse<DocumentResponse>> upload(
            @PathVariable UUID knowledgeBaseId,
            @RequestParam("file") MultipartFile file,
            HttpSession session) {
        UUID userId = authenticationService.requireUserId(session);
        DocumentResponse response = documentService.upload(userId, knowledgeBaseId, file);
        return ResponseEntity.status(HttpStatus.CREATED).body(ApiResponse.success(response));
    }

    /** 删除指定文档及其向量文本块。 */
    @DeleteMapping("/{documentId}")
    ResponseEntity<Void> delete(
            @PathVariable UUID knowledgeBaseId,
            @PathVariable UUID documentId,
            HttpSession session) {
        UUID userId = authenticationService.requireUserId(session);
        documentService.delete(userId, documentId);
        return ResponseEntity.noContent().build();
    }
}

package com.biorag.platform.knowledgebase.controller;

import com.biorag.platform.auth.service.SessionAuthenticationService;
import com.biorag.platform.common.dto.ApiResponse;
import com.biorag.platform.knowledgebase.dto.CreateKnowledgeBaseRequest;
import com.biorag.platform.knowledgebase.dto.KnowledgeBaseResponse;
import com.biorag.platform.knowledgebase.dto.UpdateKnowledgeBaseRequest;
import com.biorag.platform.knowledgebase.service.KnowledgeBaseService;
import jakarta.servlet.http.HttpSession;
import jakarta.validation.Valid;
import java.util.List;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 知识库接口控制器，负责接收 CRUD 请求并从 Session 获取当前用户。
 */
@RestController
@RequestMapping("/api/knowledge-bases")
public class KnowledgeBaseController {

    private final KnowledgeBaseService knowledgeBaseService;
    private final SessionAuthenticationService sessionAuthenticationService;

    /**
     * 注入知识库业务服务和 Session 认证服务。
     */
    public KnowledgeBaseController(
            KnowledgeBaseService knowledgeBaseService,
            SessionAuthenticationService sessionAuthenticationService) {
        this.knowledgeBaseService = knowledgeBaseService;
        this.sessionAuthenticationService = sessionAuthenticationService;
    }

    /**
     * 为当前登录用户创建知识库。
     */
    @PostMapping
    ResponseEntity<ApiResponse<KnowledgeBaseResponse>> create(
            @Valid @RequestBody CreateKnowledgeBaseRequest request,
            HttpSession session) {
        UUID currentUserId = sessionAuthenticationService.requireUserId(session);
        KnowledgeBaseResponse response = knowledgeBaseService.create(currentUserId, request);
        return ResponseEntity.status(HttpStatus.CREATED).body(ApiResponse.success(response));
    }

    /**
     * 查询当前登录用户拥有的知识库列表。
     */
    @GetMapping
    ApiResponse<List<KnowledgeBaseResponse>> list(HttpSession session) {
        UUID currentUserId = sessionAuthenticationService.requireUserId(session);
        return ApiResponse.success(knowledgeBaseService.listAccessible(currentUserId));
    }

    /**
     * 查询有权访问的指定知识库，包括自己拥有和其他人的公开知识库。
     */
    @GetMapping("/{knowledgeBaseId}")
    ApiResponse<KnowledgeBaseResponse> get(
            @PathVariable UUID knowledgeBaseId,
            HttpSession session) {
        UUID currentUserId = sessionAuthenticationService.requireUserId(session);
        return ApiResponse.success(knowledgeBaseService.getAccessible(currentUserId, knowledgeBaseId));
    }

    /**
     * 完整更新当前用户拥有的指定知识库。
     */
    @PutMapping("/{knowledgeBaseId}")
    ApiResponse<KnowledgeBaseResponse> update(
            @PathVariable UUID knowledgeBaseId,
            @Valid @RequestBody UpdateKnowledgeBaseRequest request,
            HttpSession session) {
        UUID currentUserId = sessionAuthenticationService.requireUserId(session);
        return ApiResponse.success(knowledgeBaseService.update(currentUserId, knowledgeBaseId, request));
    }

    /**
     * 删除当前用户拥有的指定知识库。
     */
    @DeleteMapping("/{knowledgeBaseId}")
    ResponseEntity<Void> delete(
            @PathVariable UUID knowledgeBaseId,
            HttpSession session) {
        UUID currentUserId = sessionAuthenticationService.requireUserId(session);
        knowledgeBaseService.delete(currentUserId, knowledgeBaseId);
        return ResponseEntity.noContent().build();
    }
}

package com.biorag.platform.knowledgebase.service;

import com.biorag.platform.auth.entity.UserAccount;
import com.biorag.platform.auth.exception.UnauthenticatedException;
import com.biorag.platform.auth.repository.UserAccountRepository;
import com.biorag.platform.auth.service.AuthService;
import com.biorag.platform.knowledgebase.dto.CreateKnowledgeBaseRequest;
import com.biorag.platform.knowledgebase.dto.KnowledgeBaseResponse;
import com.biorag.platform.knowledgebase.dto.UpdateKnowledgeBaseRequest;
import com.biorag.platform.knowledgebase.entity.KnowledgeBase;
import com.biorag.platform.knowledgebase.entity.KnowledgeBaseVisibility;
import com.biorag.platform.knowledgebase.exception.KnowledgeBaseAccessDeniedException;
import com.biorag.platform.knowledgebase.exception.KnowledgeBaseNotFoundException;
import com.biorag.platform.knowledgebase.repository.KnowledgeBaseRepository;
import java.util.List;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 知识库业务服务，负责 CRUD、所有者绑定和所有权校验。
 */
@Service
public class KnowledgeBaseService {

    private final KnowledgeBaseRepository knowledgeBaseRepository;
    private final UserAccountRepository userAccountRepository;
    private final AuthService authService;

    /**
     * 注入知识库仓库和用户仓库。
     */
    public KnowledgeBaseService(
            KnowledgeBaseRepository knowledgeBaseRepository,
            UserAccountRepository userAccountRepository,
            AuthService authService) {
        this.knowledgeBaseRepository = knowledgeBaseRepository;
        this.userAccountRepository = userAccountRepository;
        this.authService = authService;
    }

    /**
     * 为当前登录用户创建知识库，并自动将其设为所有者。
     */
    @Transactional
    public KnowledgeBaseResponse create(UUID currentUserId, CreateKnowledgeBaseRequest request) {
        UserAccount owner = requireCurrentUser(currentUserId);
        if (request.visibility() == KnowledgeBaseVisibility.BUILT_IN) {
            authService.requireAdmin(currentUserId);
        }
        KnowledgeBase knowledgeBase = new KnowledgeBase(
                request.name(), request.description(), owner, request.visibility());
        return toResponse(knowledgeBaseRepository.save(knowledgeBase), currentUserId);
    }

    /**
     * 查询当前用户拥有的全部知识库。
     */
    @Transactional(readOnly = true)
    public List<KnowledgeBaseResponse> listAccessible(UUID currentUserId) {
        requireCurrentUser(currentUserId);
        return knowledgeBaseRepository.findAllAccessible(currentUserId).stream()
                .map(knowledgeBase -> toResponse(knowledgeBase, currentUserId))
                .toList();
    }

    /**
     * 查询知识库详情，公开知识库允许其他登录用户读取。
     */
    @Transactional(readOnly = true)
    public KnowledgeBaseResponse getAccessible(UUID currentUserId, UUID knowledgeBaseId) {
        KnowledgeBase knowledgeBase = requireAccessibleEntity(currentUserId, knowledgeBaseId);
        return toResponse(knowledgeBase, currentUserId);
    }

    /**
     * 加载当前用户可读取的知识库实体，供会话等内部业务复用权限规则。
     */
    @Transactional(readOnly = true)
    public KnowledgeBase requireAccessibleEntity(UUID currentUserId, UUID knowledgeBaseId) {
        KnowledgeBase knowledgeBase = requireKnowledgeBase(knowledgeBaseId);
        boolean isOwner = knowledgeBase.getOwner().getId().equals(currentUserId);
        boolean isPublic = knowledgeBase.getVisibility() == KnowledgeBaseVisibility.PUBLIC
                || knowledgeBase.getVisibility() == KnowledgeBaseVisibility.BUILT_IN;
        if (!isOwner && !isPublic) {
            throw new KnowledgeBaseAccessDeniedException();
        }
        return knowledgeBase;
    }

    /**
     * 加载当前用户拥有的知识库实体，供文档写入等内部业务复用权限规则。
     */
    @Transactional(readOnly = true)
    public KnowledgeBase requireOwnedEntity(UUID currentUserId, UUID knowledgeBaseId) {
        return requireOwned(currentUserId, knowledgeBaseId);
    }

    /**
     * 修改知识库基本信息，仅允许所有者操作。
     */
    @Transactional
    public KnowledgeBaseResponse update(
            UUID currentUserId,
            UUID knowledgeBaseId,
            UpdateKnowledgeBaseRequest request) {
        KnowledgeBase knowledgeBase = requireOwned(currentUserId, knowledgeBaseId);
        if (knowledgeBase.getVisibility() == KnowledgeBaseVisibility.BUILT_IN
                || request.visibility() == KnowledgeBaseVisibility.BUILT_IN) {
            authService.requireAdmin(currentUserId);
        }
        knowledgeBase.update(request.name(), request.description(), request.visibility());
        return toResponse(knowledgeBase, currentUserId);
    }

    /**
     * 删除知识库，仅允许所有者操作。
     */
    @Transactional
    public void delete(UUID currentUserId, UUID knowledgeBaseId) {
        KnowledgeBase knowledgeBase = requireOwned(currentUserId, knowledgeBaseId);
        if (knowledgeBase.getVisibility() == KnowledgeBaseVisibility.BUILT_IN) {
            authService.requireAdmin(currentUserId);
        }
        knowledgeBaseRepository.delete(knowledgeBase);
    }

    /**
     * 根据 Session 用户 ID 加载用户，处理会话残留但用户已不存在的情况。
     */
    private UserAccount requireCurrentUser(UUID currentUserId) {
        return userAccountRepository.findById(currentUserId)
                .orElseThrow(UnauthenticatedException::new);
    }

    /**
     * 加载知识库并验证当前用户是否为所有者。
     */
    private KnowledgeBase requireOwned(UUID currentUserId, UUID knowledgeBaseId) {
        KnowledgeBase knowledgeBase = requireKnowledgeBase(knowledgeBaseId);
        boolean owner = knowledgeBase.getOwner().getId().equals(currentUserId);
        boolean builtInAdmin = knowledgeBase.getVisibility() == KnowledgeBaseVisibility.BUILT_IN
                && authService.isAdmin(currentUserId);
        if (!owner && !builtInAdmin) {
            throw new KnowledgeBaseAccessDeniedException();
        }
        return knowledgeBase;
    }

    /**
     * 根据 ID 加载知识库，不存在时抛出 404 异常。
     */
    private KnowledgeBase requireKnowledgeBase(UUID knowledgeBaseId) {
        return knowledgeBaseRepository.findById(knowledgeBaseId)
                .orElseThrow(() -> new KnowledgeBaseNotFoundException(knowledgeBaseId));
    }

    /**
     * 将数据库实体转换为对外响应 DTO。
     */
    private KnowledgeBaseResponse toResponse(KnowledgeBase knowledgeBase, UUID currentUserId) {
        boolean owned = knowledgeBase.getOwner().getId().equals(currentUserId);
        boolean editable = owned || (knowledgeBase.getVisibility() == KnowledgeBaseVisibility.BUILT_IN
                && authService.isAdmin(currentUserId));
        return new KnowledgeBaseResponse(
                knowledgeBase.getId(),
                knowledgeBase.getName(),
                knowledgeBase.getDescription(),
                knowledgeBase.getOwner().getId(),
                knowledgeBase.getOwner().getEmail(),
                knowledgeBase.getVisibility(),
                owned,
                editable,
                knowledgeBase.getCreatedAt(),
                knowledgeBase.getUpdatedAt());
    }
}

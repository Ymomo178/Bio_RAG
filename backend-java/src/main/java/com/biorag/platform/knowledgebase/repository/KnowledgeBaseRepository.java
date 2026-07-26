package com.biorag.platform.knowledgebase.repository;

import com.biorag.platform.knowledgebase.entity.KnowledgeBase;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

/**
 * 知识库数据访问接口，由 Spring Data JPA 自动生成实现。
 */
public interface KnowledgeBaseRepository extends JpaRepository<KnowledgeBase, UUID> {

    /**
     * 查询指定用户拥有的知识库，并按创建时间倒序排列。
     */
    List<KnowledgeBase> findAllByOwner_IdOrderByCreatedAtDesc(UUID ownerId);

    /** 查询用户自己的、其他用户公开的以及系统内置知识库。 */
    @Query("""
            SELECT knowledgeBase FROM KnowledgeBase knowledgeBase
            WHERE knowledgeBase.owner.id = :userId
               OR knowledgeBase.visibility IN (
                    com.biorag.platform.knowledgebase.entity.KnowledgeBaseVisibility.PUBLIC,
                    com.biorag.platform.knowledgebase.entity.KnowledgeBaseVisibility.BUILT_IN)
            ORDER BY knowledgeBase.visibility, knowledgeBase.createdAt DESC
            """)
    List<KnowledgeBase> findAllAccessible(@Param("userId") UUID userId);
}

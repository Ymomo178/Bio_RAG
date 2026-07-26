package com.biorag.platform.document.repository;

import com.biorag.platform.document.entity.KnowledgeDocument;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

/**
 * 知识库文档数据访问接口。
 */
public interface KnowledgeDocumentRepository extends JpaRepository<KnowledgeDocument, UUID> {

    /** 查询指定知识库中的全部文档。 */
    List<KnowledgeDocument> findAllByKnowledgeBase_IdOrderByCreatedAtDesc(UUID knowledgeBaseId);

    /** 判断同一知识库是否已经上传完全相同的文件。 */
    boolean existsByKnowledgeBase_IdAndFileHash(UUID knowledgeBaseId, String fileHash);

    /** 按文档和知识库所有者查询，防止跨用户访问。 */
    Optional<KnowledgeDocument> findByIdAndKnowledgeBase_Owner_Id(UUID id, UUID ownerId);
}

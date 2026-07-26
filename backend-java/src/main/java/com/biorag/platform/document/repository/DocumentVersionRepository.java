package com.biorag.platform.document.repository;

import com.biorag.platform.document.entity.DocumentVersion;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

/**
 * 文档版本数据访问接口。
 */
public interface DocumentVersionRepository extends JpaRepository<DocumentVersion, UUID> {

    /** 查询指定文档的全部版本。 */
    List<DocumentVersion> findAllByDocument_Id(UUID documentId);
}

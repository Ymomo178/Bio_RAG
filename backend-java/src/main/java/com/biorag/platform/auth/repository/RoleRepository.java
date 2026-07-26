package com.biorag.platform.auth.repository;

import com.biorag.platform.auth.entity.Role;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

/**
 * 系统角色数据访问接口。
 */
public interface RoleRepository extends JpaRepository<Role, UUID> {

    /** 按稳定代码查找角色。 */
    Optional<Role> findByCode(String code);
}

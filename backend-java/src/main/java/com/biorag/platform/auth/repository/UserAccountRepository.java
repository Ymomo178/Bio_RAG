package com.biorag.platform.auth.repository;

import com.biorag.platform.auth.entity.UserAccount;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

/**
 * 用户账号数据访问接口，由 Spring Data JPA 自动生成实现。
 */
public interface UserAccountRepository extends JpaRepository<UserAccount, UUID> {

    /**
     * 根据规范化邮箱查询用户。
     */
    Optional<UserAccount> findByEmail(String email);

    /**
     * 判断规范化邮箱是否已经存在。
     */
    boolean existsByEmail(String email);
}

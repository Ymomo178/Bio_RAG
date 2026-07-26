package com.biorag.platform.auth.repository;

import static org.assertj.core.api.Assertions.assertThat;

import com.biorag.platform.auth.entity.UserAccount;
import com.biorag.platform.auth.entity.UserStatus;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.test.context.ActiveProfiles;

/**
 * 用户仓库的数据访问测试，使用 H2 和真实 JPA 映射。
 */
@DataJpaTest(properties = "debug=false")
@ActiveProfiles("test")
class UserAccountRepositoryTest {

    @Autowired
    private UserAccountRepository repository;

    /**
     * 验证用户可以保存，并能通过邮箱重新查询。
     */
    @Test
    void savesAndFindsUserByEmail() {
        UserAccount saved = repository.saveAndFlush(
                new UserAccount("analyst@example.com", "bcrypt-hash-placeholder"));

        assertThat(saved.getId()).isNotNull();
        assertThat(saved.getStatus()).isEqualTo(UserStatus.ACTIVE);
        assertThat(saved.getCreatedAt()).isNotNull();
        assertThat(repository.findByEmail("analyst@example.com"))
                .isPresent()
                .get()
                .extracting(UserAccount::getEmail)
                .isEqualTo("analyst@example.com");
    }

    /**
     * 验证邮箱存在性查询的正确与错误分支。
     */
    @Test
    void reportsWhetherEmailAlreadyExists() {
        repository.saveAndFlush(new UserAccount("admin@example.com", "bcrypt-hash-placeholder"));

        assertThat(repository.existsByEmail("admin@example.com")).isTrue();
        assertThat(repository.existsByEmail("missing@example.com")).isFalse();
    }
}

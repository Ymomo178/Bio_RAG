package com.biorag.platform.auth.service;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.Mockito.mock;

import com.biorag.platform.auth.repository.RoleRepository;
import com.biorag.platform.auth.repository.UserAccountRepository;
import org.junit.jupiter.api.Test;

/**
 * 验证不同运行环境下管理员邮箱的启动校验规则。
 */
class AdminRoleBootstrapTest {

    /** 容器和生产环境要求管理员邮箱时，空配置必须阻止应用启动。 */
    @Test
    void rejectsMissingRequiredAdminEmail() {
        AdminRoleBootstrap bootstrap = bootstrap("", true);

        assertThrows(IllegalStateException.class, () -> bootstrap.run(null));
    }

    /** 本地开发允许暂时不设置管理员邮箱。 */
    @Test
    void allowsMissingOptionalAdminEmail() {
        AdminRoleBootstrap bootstrap = bootstrap("", false);

        assertDoesNotThrow(() -> bootstrap.run(null));
    }

    /** 创建只用于启动配置校验的服务实例。 */
    private AdminRoleBootstrap bootstrap(String email, boolean required) {
        return new AdminRoleBootstrap(
                mock(UserAccountRepository.class),
                mock(RoleRepository.class),
                email,
                required);
    }
}

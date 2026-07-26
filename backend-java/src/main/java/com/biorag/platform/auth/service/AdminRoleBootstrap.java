package com.biorag.platform.auth.service;

import com.biorag.platform.auth.repository.RoleRepository;
import com.biorag.platform.auth.repository.UserAccountRepository;
import java.util.Locale;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

/**
 * 应用启动时把配置邮箱对应的已有账号提升为管理员。
 */
@Component
public class AdminRoleBootstrap implements ApplicationRunner {
    private final UserAccountRepository users;
    private final RoleRepository roles;
    private final String adminEmail;

    /** 注入账号、角色仓库和管理员邮箱配置。 */
    public AdminRoleBootstrap(UserAccountRepository users, RoleRepository roles,
            @Value("${app.admin-email:}") String adminEmail) {
        this.users = users;
        this.roles = roles;
        this.adminEmail = adminEmail.strip().toLowerCase(Locale.ROOT);
    }

    /** 在数据库迁移完成后幂等补充管理员角色。 */
    @Override
    @Transactional
    public void run(ApplicationArguments arguments) {
        if (adminEmail.isBlank()) return;
        users.findByEmail(adminEmail).ifPresent(user -> {
            if (!user.hasRole("ADMIN")) {
                user.addRole(roles.findByCode("ADMIN")
                        .orElseThrow(() -> new IllegalStateException("ADMIN 角色未初始化")));
            }
        });
    }
}

package com.biorag.platform.admin.service;

import com.biorag.platform.admin.dto.AdminUserResponse;
import com.biorag.platform.admin.dto.UpdateUserRequest;
import com.biorag.platform.auth.entity.UserAccount;
import com.biorag.platform.auth.entity.UserStatus;
import com.biorag.platform.auth.repository.RoleRepository;
import com.biorag.platform.auth.repository.UserAccountRepository;
import com.biorag.platform.auth.service.AuthService;
import java.util.List;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** 管理员业务服务，负责用户账号和角色管理。 */
@Service
public class AdminService {
    private final AuthService authService;
    private final UserAccountRepository users;
    private final RoleRepository roles;

    /** 注入权限校验和账号数据访问依赖。 */
    public AdminService(AuthService authService, UserAccountRepository users, RoleRepository roles) {
        this.authService = authService;
        this.users = users;
        this.roles = roles;
    }

    /** 返回全部用户，调用者必须是管理员。 */
    @Transactional(readOnly = true)
    public List<AdminUserResponse> listUsers(UUID currentUserId) {
        authService.requireAdmin(currentUserId);
        return users.findAll().stream().map(this::toResponse).toList();
    }

    /** 修改其他用户的启用状态和管理员角色。 */
    @Transactional
    public AdminUserResponse updateUser(UUID currentUserId, UUID userId, UpdateUserRequest request) {
        authService.requireAdmin(currentUserId);
        if (currentUserId.equals(userId)) {
            throw new IllegalArgumentException("不能在此处修改自己的管理员权限或状态");
        }
        UserAccount user = users.findById(userId).orElseThrow(() -> new IllegalArgumentException("用户不存在"));
        if (request.status() == UserStatus.ACTIVE) user.enable(); else user.disable();
        var adminRole = roles.findByCode("ADMIN").orElseThrow();
        if (request.admin()) user.addRole(adminRole); else user.removeRole(adminRole);
        return toResponse(user);
    }

    /** 将账号转换为安全的管理员响应。 */
    private AdminUserResponse toResponse(UserAccount user) {
        return new AdminUserResponse(user.getId(), user.getEmail(), user.getStatus(),
                user.getRoles().stream().map(role -> role.getCode()).sorted().toList(), user.getCreatedAt());
    }
}

package com.biorag.platform.auth.service;

import com.biorag.platform.auth.dto.LoginRequest;
import com.biorag.platform.auth.dto.LoginResponse;
import com.biorag.platform.auth.dto.RegisterRequest;
import com.biorag.platform.auth.dto.RegisterResponse;
import com.biorag.platform.auth.entity.UserAccount;
import com.biorag.platform.auth.entity.UserStatus;
import com.biorag.platform.auth.exception.AccountDisabledException;
import com.biorag.platform.auth.exception.DuplicateEmailException;
import com.biorag.platform.auth.exception.InvalidCredentialsException;
import com.biorag.platform.auth.exception.UnauthenticatedException;
import com.biorag.platform.auth.repository.UserAccountRepository;
import com.biorag.platform.auth.repository.RoleRepository;
import java.util.List;
import java.util.Locale;
import java.util.UUID;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 认证业务服务，负责注册流程中的业务规则和数据库写入。
 */
@Service
public class AuthService {

    private final UserAccountRepository userAccountRepository;
    private final PasswordEncoder passwordEncoder;
    private final RoleRepository roleRepository;
    private final String configuredAdminEmail;

    /**
     * 注入用户仓库和密码编码器。
     */
    public AuthService(
            UserAccountRepository userAccountRepository,
            PasswordEncoder passwordEncoder,
            RoleRepository roleRepository,
            @Value("${app.admin-email:}") String configuredAdminEmail) {
        this.userAccountRepository = userAccountRepository;
        this.passwordEncoder = passwordEncoder;
        this.roleRepository = roleRepository;
        this.configuredAdminEmail = configuredAdminEmail.strip().toLowerCase(Locale.ROOT);
    }

    /**
     * 规范化邮箱、检查重复、加密密码并创建用户。
     */
    @Transactional
    public RegisterResponse register(RegisterRequest request) {
        String normalizedEmail = request.email().trim().toLowerCase(Locale.ROOT);

        if (userAccountRepository.existsByEmail(normalizedEmail)) {
            throw new DuplicateEmailException(normalizedEmail);
        }

        String passwordHash = passwordEncoder.encode(request.password());
        UserAccount saved = userAccountRepository.save(
                new UserAccount(normalizedEmail, passwordHash));
        assignDefaultRoles(saved);

        return new RegisterResponse(saved.getId(), saved.getEmail(), saved.getStatus(), roleCodes(saved));
    }

    /**
     * 根据邮箱查找用户，校验 BCrypt 密码并检查账号状态。
     */
    @Transactional
    public LoginResponse login(LoginRequest request) {
        String normalizedEmail = request.email().trim().toLowerCase(Locale.ROOT);
        UserAccount user = userAccountRepository.findByEmail(normalizedEmail)
                .orElseThrow(InvalidCredentialsException::new);

        if (!passwordEncoder.matches(request.password(), user.getPasswordHash())) {
            throw new InvalidCredentialsException();
        }

        if (user.getStatus() != UserStatus.ACTIVE) {
            throw new AccountDisabledException();
        }
        assignDefaultRoles(user);

        return toLoginResponse(user);
    }

    /**
     * 根据 Session 中的用户 ID 返回当前登录账号信息。
     */
    @Transactional
    public LoginResponse current(UUID userId) {
        UserAccount user = userAccountRepository.findById(userId)
                .orElseThrow(UnauthenticatedException::new);
        if (user.getStatus() != UserStatus.ACTIVE) {
            throw new AccountDisabledException();
        }
        assignDefaultRoles(user);
        return toLoginResponse(user);
    }

    /** 验证指定用户具有管理员角色。 */
    @Transactional(readOnly = true)
    public UserAccount requireAdmin(UUID userId) {
        UserAccount user = userAccountRepository.findById(userId)
                .orElseThrow(UnauthenticatedException::new);
        if (!user.hasRole("ADMIN")) {
            throw new com.biorag.platform.auth.exception.AdminAccessDeniedException();
        }
        return user;
    }

    /** 判断指定登录用户是否具有管理员角色。 */
    @Transactional(readOnly = true)
    public boolean isAdmin(UUID userId) {
        return userAccountRepository.findById(userId)
                .map(user -> user.hasRole("ADMIN"))
                .orElse(false);
    }

    /** 为账号补充 USER 角色，并按配置邮箱授予管理员权限。 */
    private void assignDefaultRoles(UserAccount user) {
        if (!user.hasRole("USER")) {
            user.addRole(roleRepository.findByCode("USER")
                    .orElseThrow(() -> new IllegalStateException("USER 角色未初始化")));
        }
        if (!configuredAdminEmail.isBlank()
                && user.getEmail().equals(configuredAdminEmail)
                && !user.hasRole("ADMIN")) {
            user.addRole(roleRepository.findByCode("ADMIN")
                    .orElseThrow(() -> new IllegalStateException("ADMIN 角色未初始化")));
        }
    }

    /** 将账号转换为登录响应。 */
    private LoginResponse toLoginResponse(UserAccount user) {
        return new LoginResponse(user.getId(), user.getEmail(), user.getStatus(), roleCodes(user));
    }

    /** 返回排序稳定的角色代码列表。 */
    private List<String> roleCodes(UserAccount user) {
        return user.getRoles().stream().map(role -> role.getCode()).sorted().toList();
    }
}

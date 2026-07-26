package com.biorag.platform.auth.service;

import com.biorag.platform.auth.exception.UnauthenticatedException;
import com.biorag.platform.auth.exception.AccountDisabledException;
import com.biorag.platform.auth.entity.UserStatus;
import com.biorag.platform.auth.repository.UserAccountRepository;
import jakarta.servlet.http.HttpSession;
import java.util.UUID;
import org.springframework.stereotype.Service;

/**
 * Session 认证服务，负责保存、读取和清除当前登录用户。
 */
@Service
public class SessionAuthenticationService {

    private static final String USER_ID_ATTRIBUTE = "AUTHENTICATED_USER_ID";
    private final UserAccountRepository users;

    /** 注入用户仓库，使停用账号的旧 Session 立即失效。 */
    public SessionAuthenticationService(UserAccountRepository users) {
        this.users = users;
    }

    /**
     * 登录成功后把用户 ID 写入服务端 Session。
     */
    public void signIn(HttpSession session, UUID userId) {
        session.setAttribute(USER_ID_ATTRIBUTE, userId);
    }

    /**
     * 从 Session 取得当前用户 ID，无有效身份时抛出 401 异常。
     */
    public UUID requireUserId(HttpSession session) {
        Object value = session.getAttribute(USER_ID_ATTRIBUTE);
        if (value instanceof UUID userId) {
            var user = users.findById(userId).orElseThrow(UnauthenticatedException::new);
            if (user.getStatus() != UserStatus.ACTIVE) {
                throw new AccountDisabledException();
            }
            return userId;
        }
        throw new UnauthenticatedException();
    }

    /**
     * 注销并销毁现有 Session；没有 Session 时保持幂等。
     */
    public void signOut(HttpSession session) {
        if (session != null) {
            session.invalidate();
        }
    }
}

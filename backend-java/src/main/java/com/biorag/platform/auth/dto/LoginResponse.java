package com.biorag.platform.auth.dto;

import com.biorag.platform.auth.entity.UserStatus;
import java.util.List;
import java.util.UUID;

/**
 * 登录验证成功后的临时响应，后续接入 JWT 时会增加访问令牌。
 */
public record LoginResponse(UUID id, String email, UserStatus status, List<String> roles) {
}

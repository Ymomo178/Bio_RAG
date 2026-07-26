package com.biorag.platform.admin.dto;

import com.biorag.platform.auth.entity.UserStatus;
import java.time.Instant;
import java.util.List;
import java.util.UUID;

/** 管理员查看的用户摘要，不包含密码哈希。 */
public record AdminUserResponse(
        UUID id, String email, UserStatus status, List<String> roles, Instant createdAt) {
}

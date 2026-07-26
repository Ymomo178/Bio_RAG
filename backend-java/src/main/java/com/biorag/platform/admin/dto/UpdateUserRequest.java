package com.biorag.platform.admin.dto;

import com.biorag.platform.auth.entity.UserStatus;
import jakarta.validation.constraints.NotNull;

/** 管理员修改用户状态和管理员角色的请求。 */
public record UpdateUserRequest(@NotNull UserStatus status, boolean admin) {
}

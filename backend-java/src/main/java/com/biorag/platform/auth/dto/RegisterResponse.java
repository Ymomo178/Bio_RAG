package com.biorag.platform.auth.dto;

import com.biorag.platform.auth.entity.UserStatus;
import java.util.List;
import java.util.UUID;

/**
 * 用户注册成功后的响应，不包含原始密码和密码哈希。
 */
public record RegisterResponse(UUID id, String email, UserStatus status, List<String> roles) {
}

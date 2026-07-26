package com.biorag.platform.auth.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/**
 * 用户注册请求，只承载客户端允许提交的邮箱和原始密码。
 */
public record RegisterRequest(
        @NotBlank(message = "email is required")
        @Email(message = "email format is invalid")
        @Size(max = 255, message = "email must not exceed 255 characters")
        String email,

        @NotBlank(message = "password is required")
        @Size(min = 8, max = 72, message = "password must contain 8 to 72 characters")
        String password) {

    /**
     * 在参数校验前去除邮箱首尾空格，避免合法邮箱因空格被误判。
     */
    public RegisterRequest {
        if (email != null) {
            email = email.trim();
        }
    }
}

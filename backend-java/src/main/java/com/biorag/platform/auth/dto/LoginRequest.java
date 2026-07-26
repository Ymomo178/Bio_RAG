package com.biorag.platform.auth.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/**
 * 用户登录请求，承载客户端提交的邮箱和原始密码。
 */
public record LoginRequest(
        @NotBlank(message = "邮箱不能为空")
        @Email(message = "邮箱格式不正确")
        @Size(max = 255, message = "邮箱长度不能超过 255 个字符")
        String email,

        @NotBlank(message = "密码不能为空")
        @Size(min = 8, max = 72, message = "密码长度必须为 8 到 72 个字符")
        String password) {

    /**
     * 在参数校验前去除邮箱首尾空格。
     */
    public LoginRequest {
        if (email != null) {
            email = email.trim();
        }
    }
}

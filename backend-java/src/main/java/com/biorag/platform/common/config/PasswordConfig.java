package com.biorag.platform.common.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;

/**
 * 密码处理配置，集中创建项目使用的密码编码器。
 */
@Configuration
public class PasswordConfig {

    /**
     * 创建 BCrypt 密码编码器，供注册和后续登录校验使用。
     */
    @Bean
    PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }
}

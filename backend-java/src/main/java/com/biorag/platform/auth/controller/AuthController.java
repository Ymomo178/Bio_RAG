package com.biorag.platform.auth.controller;

import com.biorag.platform.auth.dto.LoginRequest;
import com.biorag.platform.auth.dto.LoginResponse;
import com.biorag.platform.auth.dto.RegisterRequest;
import com.biorag.platform.auth.dto.RegisterResponse;
import com.biorag.platform.auth.service.AuthService;
import com.biorag.platform.auth.service.SessionAuthenticationService;
import com.biorag.platform.common.dto.ApiResponse;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpSession;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 认证接口控制器，负责接收和响应注册等 HTTP 请求。
 */
@RestController
@RequestMapping("/api/auth")
public class AuthController {

    private final AuthService authService;
    private final SessionAuthenticationService sessionAuthenticationService;

    /**
     * 通过构造方法注入认证业务服务。
     */
    public AuthController(
            AuthService authService,
            SessionAuthenticationService sessionAuthenticationService) {
        this.authService = authService;
        this.sessionAuthenticationService = sessionAuthenticationService;
    }

    /**
     * 返回当前浏览器 Session 对应的登录用户。
     */
    @GetMapping("/me")
    ApiResponse<LoginResponse> me(HttpSession session) {
        return ApiResponse.success(
                authService.current(sessionAuthenticationService.requireUserId(session)));
    }

    /**
     * 校验注册参数并创建用户，成功时返回 HTTP 201。
     */
    @PostMapping("/register")
    ResponseEntity<ApiResponse<RegisterResponse>> register(@Valid @RequestBody RegisterRequest request) {
        RegisterResponse response = authService.register(request);
        return ResponseEntity.status(HttpStatus.CREATED).body(ApiResponse.success(response));
    }

    /**
     * 校验用户邮箱和密码，成功后建立服务端登录会话。
     */
    @PostMapping("/login")
    ApiResponse<LoginResponse> login(
            @Valid @RequestBody LoginRequest request,
            HttpServletRequest servletRequest) {
        LoginResponse response = authService.login(request);
        HttpSession session = servletRequest.getSession(true);
        servletRequest.changeSessionId();
        sessionAuthenticationService.signIn(session, response.id());
        return ApiResponse.success(response);
    }

    /**
     * 注销当前用户并销毁服务端会话。
     */
    @PostMapping("/logout")
    ResponseEntity<Void> logout(HttpServletRequest servletRequest) {
        sessionAuthenticationService.signOut(servletRequest.getSession(false));
        return ResponseEntity.noContent().build();
    }
}

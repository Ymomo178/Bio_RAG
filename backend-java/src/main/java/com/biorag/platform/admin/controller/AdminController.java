package com.biorag.platform.admin.controller;

import com.biorag.platform.admin.dto.AdminUserResponse;
import com.biorag.platform.admin.dto.UpdateUserRequest;
import com.biorag.platform.admin.service.AdminService;
import com.biorag.platform.auth.service.SessionAuthenticationService;
import com.biorag.platform.common.dto.ApiResponse;
import jakarta.servlet.http.HttpSession;
import jakarta.validation.Valid;
import java.util.List;
import java.util.UUID;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/** 管理员接口控制器，只暴露用户管理能力。 */
@RestController
@RequestMapping("/api/admin")
public class AdminController {
    private final AdminService adminService;
    private final SessionAuthenticationService authentication;

    /** 注入管理员业务和 Session 认证服务。 */
    public AdminController(AdminService adminService, SessionAuthenticationService authentication) {
        this.adminService = adminService;
        this.authentication = authentication;
    }

    /** 返回全部用户。 */
    @GetMapping("/users")
    ApiResponse<List<AdminUserResponse>> listUsers(HttpSession session) {
        return ApiResponse.success(adminService.listUsers(authentication.requireUserId(session)));
    }

    /** 修改指定用户。 */
    @PutMapping("/users/{userId}")
    ApiResponse<AdminUserResponse> updateUser(@PathVariable UUID userId,
            @Valid @RequestBody UpdateUserRequest request, HttpSession session) {
        return ApiResponse.success(adminService.updateUser(authentication.requireUserId(session), userId, request));
    }
}

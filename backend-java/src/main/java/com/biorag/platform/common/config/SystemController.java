package com.biorag.platform.common.config;

import com.biorag.platform.common.dto.ApiResponse;
import com.biorag.platform.common.dto.SystemHealth;
import com.biorag.platform.common.service.SystemService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 系统公共接口控制器，目前提供基础健康检查。
 */
@RestController
@RequestMapping("/api/v1/system")
public class SystemController {

    private final SystemService systemService;

    /**
     * 通过构造方法注入系统服务。
     */
    public SystemController(SystemService systemService) {
        this.systemService = systemService;
    }

    /**
     * 返回 Java 后端的基础运行状态。
     */
    @GetMapping("/health")
    ApiResponse<SystemHealth> health() {
        return ApiResponse.success(systemService.health());
    }
}

package com.biorag.platform.common.service;

import static org.assertj.core.api.Assertions.assertThat;

import com.biorag.platform.common.dto.SystemHealth;
import org.junit.jupiter.api.Test;

/**
 * 系统服务的纯单元测试，不启动 Spring 容器。
 */
class SystemServiceTest {

    private final SystemService systemService = new SystemService();

    /**
     * 验证服务名称和健康状态符合约定。
     */
    @Test
    void returnsBackendHealth() {
        SystemHealth health = systemService.health();

        assertThat(health.service()).isEqualTo("bio-rag-backend");
        assertThat(health.status()).isEqualTo("UP");
    }
}

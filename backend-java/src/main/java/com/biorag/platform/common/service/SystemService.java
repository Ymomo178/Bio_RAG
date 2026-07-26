package com.biorag.platform.common.service;

import com.biorag.platform.common.dto.SystemHealth;
import org.springframework.stereotype.Service;

/**
 * 系统公共业务服务，负责生成系统运行状态等信息。
 */
@Service
public class SystemService {

    /**
     * 返回当前 Java 后端的基础健康状态。
     */
    public SystemHealth health() {
        return new SystemHealth("bio-rag-backend", "UP");
    }
}

package com.biorag.platform.common.dto;

/**
 * 系统健康信息，描述服务名称和当前状态。
 */
public record SystemHealth(String service, String status) {
}

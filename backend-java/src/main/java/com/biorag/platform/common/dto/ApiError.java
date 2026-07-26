package com.biorag.platform.common.dto;

/**
 * 统一错误信息，包含稳定错误码和可读错误说明。
 */
public record ApiError(String code, String message) {
}

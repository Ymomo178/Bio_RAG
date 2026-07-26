package com.biorag.platform.auth.exception;

/**
 * 请求没有有效登录会话时抛出的认证异常。
 */
public class UnauthenticatedException extends RuntimeException {

    /**
     * 使用固定的未登录信息创建异常。
     */
    public UnauthenticatedException() {
        super("请先登录");
    }
}

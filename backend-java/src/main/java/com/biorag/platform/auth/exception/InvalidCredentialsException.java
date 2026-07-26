package com.biorag.platform.auth.exception;

/**
 * 登录邮箱不存在或密码不正确时抛出的统一认证异常。
 */
public class InvalidCredentialsException extends RuntimeException {

    /**
     * 使用不暴露具体失败原因的固定信息创建异常。
     */
    public InvalidCredentialsException() {
        super("邮箱或密码错误");
    }
}

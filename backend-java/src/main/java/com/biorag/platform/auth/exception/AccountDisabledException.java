package com.biorag.platform.auth.exception;

/**
 * 用户凭据正确但账号已停用时抛出的业务异常。
 */
public class AccountDisabledException extends RuntimeException {

    /**
     * 使用固定的账号停用信息创建异常。
     */
    public AccountDisabledException() {
        super("账号已停用");
    }
}

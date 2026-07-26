package com.biorag.platform.auth.exception;

/**
 * 注册邮箱已存在时抛出的业务异常。
 */
public class DuplicateEmailException extends RuntimeException {

    /**
     * 使用发生冲突的规范化邮箱构造异常信息。
     */
    public DuplicateEmailException(String email) {
        super("Email is already registered: " + email);
    }
}

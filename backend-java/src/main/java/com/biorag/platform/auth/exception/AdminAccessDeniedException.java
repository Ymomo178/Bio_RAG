package com.biorag.platform.auth.exception;

/**
 * 当前登录用户尝试访问管理员功能时抛出的异常。
 */
public class AdminAccessDeniedException extends RuntimeException {

    /** 创建固定且不泄露内部信息的权限异常。 */
    public AdminAccessDeniedException() {
        super("该操作需要管理员权限");
    }
}

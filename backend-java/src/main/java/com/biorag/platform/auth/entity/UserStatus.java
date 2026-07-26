package com.biorag.platform.auth.entity;

/**
 * 用户账号状态，用于控制账号是否允许正常使用。
 */
public enum UserStatus {
    /** 正常可用。 */
    ACTIVE,
    /** 已被停用。 */
    DISABLED
}

package com.biorag.platform.knowledgebase.entity;

/**
 * 知识库可见范围，支持私有、用户公开和系统内置三种状态。
 */
public enum KnowledgeBaseVisibility {
    /** 只有所有者和后续授权成员可以访问。 */
    PRIVATE,
    /** 登录用户可以查看，修改权限仍属于所有者。 */
    PUBLIC,
    /** 只有管理员可以维护，所有登录用户都可以使用。 */
    BUILT_IN
}

package com.biorag.platform.document.entity;

/**
 * 表示上传文档当前所处的处理阶段。
 */
public enum DocumentStatus {
    UPLOADED,
    INDEXING,
    READY,
    FAILED
}

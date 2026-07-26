package com.biorag.platform.document.exception;

import java.util.UUID;

/**
 * 当前用户无法找到指定文档时抛出的异常。
 */
public class DocumentNotFoundException extends RuntimeException {

    /** 使用文档 ID 创建错误。 */
    public DocumentNotFoundException(UUID documentId) {
        super("文档不存在或无权访问：" + documentId);
    }
}

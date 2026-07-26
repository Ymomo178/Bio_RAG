package com.biorag.platform.document.exception;

/**
 * 上传空文件或不支持格式时抛出的异常。
 */
public class UnsupportedDocumentException extends RuntimeException {

    /** 使用具体原因创建文档校验错误。 */
    public UnsupportedDocumentException(String message) {
        super(message);
    }
}

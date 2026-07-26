package com.biorag.platform.document.exception;

/**
 * 同一知识库重复上传相同内容时抛出的异常。
 */
public class DuplicateDocumentException extends RuntimeException {

    /** 创建重复文件错误。 */
    public DuplicateDocumentException() {
        super("该知识库已经存在内容完全相同的文件");
    }
}

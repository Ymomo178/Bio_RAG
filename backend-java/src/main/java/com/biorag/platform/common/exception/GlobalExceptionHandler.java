package com.biorag.platform.common.exception;

import com.biorag.platform.auth.exception.AccountDisabledException;
import com.biorag.platform.auth.exception.AdminAccessDeniedException;
import com.biorag.platform.auth.exception.DuplicateEmailException;
import com.biorag.platform.auth.exception.InvalidCredentialsException;
import com.biorag.platform.auth.exception.UnauthenticatedException;
import com.biorag.platform.chat.exception.ConversationNotFoundException;
import com.biorag.platform.common.dto.ApiResponse;
import com.biorag.platform.document.exception.DocumentNotFoundException;
import com.biorag.platform.document.exception.DuplicateDocumentException;
import com.biorag.platform.document.exception.UnsupportedDocumentException;
import com.biorag.platform.integration.ai.AiServiceException;
import com.biorag.platform.knowledgebase.exception.KnowledgeBaseAccessDeniedException;
import com.biorag.platform.knowledgebase.exception.KnowledgeBaseNotFoundException;
import java.util.stream.Collectors;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

/**
 * 全局异常处理器，将 Java 异常统一转换成稳定的 HTTP 错误响应。
 */
@RestControllerAdvice
public class GlobalExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    /**
     * 将重复邮箱异常映射为 HTTP 409。
     */
    @ExceptionHandler(DuplicateEmailException.class)
    public ResponseEntity<ApiResponse<Void>> handleDuplicateEmail(DuplicateEmailException exception) {
        return ResponseEntity.status(HttpStatus.CONFLICT)
                .body(ApiResponse.failure("EMAIL_ALREADY_EXISTS", exception.getMessage()));
    }

    /**
     * 将无效登录凭据映射为 HTTP 401，且不区分邮箱和密码错误。
     */
    @ExceptionHandler(InvalidCredentialsException.class)
    public ResponseEntity<ApiResponse<Void>> handleInvalidCredentials(InvalidCredentialsException exception) {
        return ResponseEntity.status(HttpStatus.UNAUTHORIZED)
                .body(ApiResponse.failure("INVALID_CREDENTIALS", exception.getMessage()));
    }

    /**
     * 将未登录异常映射为 HTTP 401。
     */
    @ExceptionHandler(UnauthenticatedException.class)
    public ResponseEntity<ApiResponse<Void>> handleUnauthenticated(UnauthenticatedException exception) {
        return ResponseEntity.status(HttpStatus.UNAUTHORIZED)
                .body(ApiResponse.failure("UNAUTHENTICATED", exception.getMessage()));
    }

    /**
     * 将账号停用异常映射为 HTTP 403。
     */
    @ExceptionHandler(AccountDisabledException.class)
    public ResponseEntity<ApiResponse<Void>> handleAccountDisabled(AccountDisabledException exception) {
        return ResponseEntity.status(HttpStatus.FORBIDDEN)
                .body(ApiResponse.failure("ACCOUNT_DISABLED", exception.getMessage()));
    }

    /** 将管理员权限不足映射为 HTTP 403。 */
    @ExceptionHandler(AdminAccessDeniedException.class)
    public ResponseEntity<ApiResponse<Void>> handleAdminAccessDenied(AdminAccessDeniedException exception) {
        return ResponseEntity.status(HttpStatus.FORBIDDEN)
                .body(ApiResponse.failure("ADMIN_ACCESS_DENIED", exception.getMessage()));
    }

    /**
     * 将知识库无权访问异常映射为 HTTP 403。
     */
    @ExceptionHandler(KnowledgeBaseAccessDeniedException.class)
    public ResponseEntity<ApiResponse<Void>> handleKnowledgeBaseAccessDenied(
            KnowledgeBaseAccessDeniedException exception) {
        return ResponseEntity.status(HttpStatus.FORBIDDEN)
                .body(ApiResponse.failure("KNOWLEDGE_BASE_ACCESS_DENIED", exception.getMessage()));
    }

    /**
     * 将知识库不存在异常映射为 HTTP 404。
     */
    @ExceptionHandler(KnowledgeBaseNotFoundException.class)
    public ResponseEntity<ApiResponse<Void>> handleKnowledgeBaseNotFound(
            KnowledgeBaseNotFoundException exception) {
        return ResponseEntity.status(HttpStatus.NOT_FOUND)
                .body(ApiResponse.failure("KNOWLEDGE_BASE_NOT_FOUND", exception.getMessage()));
    }

    /** 将会话不存在或无权访问映射为 HTTP 404。 */
    @ExceptionHandler(ConversationNotFoundException.class)
    public ResponseEntity<ApiResponse<Void>> handleConversationNotFound(
            ConversationNotFoundException exception) {
        return ResponseEntity.status(HttpStatus.NOT_FOUND)
                .body(ApiResponse.failure("CONVERSATION_NOT_FOUND", exception.getMessage()));
    }

    /** 将文档不存在或无权访问映射为 HTTP 404。 */
    @ExceptionHandler(DocumentNotFoundException.class)
    public ResponseEntity<ApiResponse<Void>> handleDocumentNotFound(
            DocumentNotFoundException exception) {
        return ResponseEntity.status(HttpStatus.NOT_FOUND)
                .body(ApiResponse.failure("DOCUMENT_NOT_FOUND", exception.getMessage()));
    }

    /** 将重复文档映射为 HTTP 409。 */
    @ExceptionHandler(DuplicateDocumentException.class)
    public ResponseEntity<ApiResponse<Void>> handleDuplicateDocument(
            DuplicateDocumentException exception) {
        return ResponseEntity.status(HttpStatus.CONFLICT)
                .body(ApiResponse.failure("DOCUMENT_ALREADY_EXISTS", exception.getMessage()));
    }

    /** 将不支持的上传文件映射为 HTTP 400。 */
    @ExceptionHandler(UnsupportedDocumentException.class)
    public ResponseEntity<ApiResponse<Void>> handleUnsupportedDocument(
            UnsupportedDocumentException exception) {
        return ResponseEntity.badRequest()
                .body(ApiResponse.failure("UNSUPPORTED_DOCUMENT", exception.getMessage()));
    }

    /** 将 Python AI 服务故障映射为 HTTP 503。 */
    @ExceptionHandler(AiServiceException.class)
    public ResponseEntity<ApiResponse<Void>> handleAiService(AiServiceException exception) {
        log.warn("AI service request failed", exception);
        return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)
                .body(ApiResponse.failure("AI_SERVICE_UNAVAILABLE", exception.getMessage()));
    }

    /**
     * 汇总 DTO 字段校验错误并映射为 HTTP 400。
     */
    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ApiResponse<Void>> handleValidation(MethodArgumentNotValidException exception) {
        String message = exception.getBindingResult().getFieldErrors().stream()
                .map(error -> error.getField() + ": " + error.getDefaultMessage())
                .collect(Collectors.joining("; "));
        return ResponseEntity.badRequest().body(ApiResponse.failure("VALIDATION_ERROR", message));
    }

    /** 将明确的业务参数错误映射为 HTTP 400。 */
    @ExceptionHandler(IllegalArgumentException.class)
    public ResponseEntity<ApiResponse<Void>> handleIllegalArgument(IllegalArgumentException exception) {
        return ResponseEntity.badRequest().body(ApiResponse.failure("INVALID_REQUEST", exception.getMessage()));
    }

    /**
     * 记录未预期异常，并向客户端返回不暴露内部细节的 HTTP 500。
     */
    @ExceptionHandler(Exception.class)
    public ResponseEntity<ApiResponse<Void>> handleUnexpected(Exception exception) {
        log.error("Unhandled request error", exception);
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(ApiResponse.failure("INTERNAL_ERROR", "The server could not process the request"));
    }
}

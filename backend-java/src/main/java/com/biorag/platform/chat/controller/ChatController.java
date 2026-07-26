package com.biorag.platform.chat.controller;

import com.biorag.platform.auth.service.SessionAuthenticationService;
import com.biorag.platform.chat.dto.ChatMessageResponse;
import com.biorag.platform.chat.dto.ChatTurnResponse;
import com.biorag.platform.chat.dto.ConversationResponse;
import com.biorag.platform.chat.dto.CreateConversationRequest;
import com.biorag.platform.chat.dto.SendMessageRequest;
import com.biorag.platform.chat.service.ChatService;
import com.biorag.platform.common.dto.ApiResponse;
import jakarta.servlet.http.HttpSession;
import jakarta.validation.Valid;
import java.util.List;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 会话接口控制器，网页只通过这里发起和恢复问答。
 */
@RestController
@RequestMapping("/api/conversations")
public class ChatController {

    private final ChatService chatService;
    private final SessionAuthenticationService authenticationService;

    /** 注入会话业务和 Session 认证服务。 */
    public ChatController(
            ChatService chatService,
            SessionAuthenticationService authenticationService) {
        this.chatService = chatService;
        this.authenticationService = authenticationService;
    }

    /** 创建一个新的持久化会话。 */
    @PostMapping
    ResponseEntity<ApiResponse<ConversationResponse>> create(
            @Valid @RequestBody CreateConversationRequest request,
            HttpSession session) {
        UUID userId = authenticationService.requireUserId(session);
        return ResponseEntity.status(HttpStatus.CREATED)
                .body(ApiResponse.success(chatService.create(userId, request)));
    }

    /** 返回当前登录用户的会话列表。 */
    @GetMapping
    ApiResponse<List<ConversationResponse>> list(HttpSession session) {
        UUID userId = authenticationService.requireUserId(session);
        return ApiResponse.success(chatService.list(userId));
    }

    /** 返回指定会话的完整消息记录。 */
    @GetMapping("/{conversationId}/messages")
    ApiResponse<List<ChatMessageResponse>> listMessages(
            @PathVariable UUID conversationId,
            HttpSession session) {
        UUID userId = authenticationService.requireUserId(session);
        return ApiResponse.success(chatService.listMessages(userId, conversationId));
    }

    /** 向会话发送新问题并返回已经持久化的一轮问答。 */
    @PostMapping("/{conversationId}/messages")
    ApiResponse<ChatTurnResponse> sendMessage(
            @PathVariable UUID conversationId,
            @Valid @RequestBody SendMessageRequest request,
            HttpSession session) {
        UUID userId = authenticationService.requireUserId(session);
        return ApiResponse.success(
                chatService.sendMessage(userId, conversationId, request.content()));
    }

    /** 删除指定会话和其中的消息。 */
    @DeleteMapping("/{conversationId}")
    ResponseEntity<Void> delete(
            @PathVariable UUID conversationId,
            HttpSession session) {
        UUID userId = authenticationService.requireUserId(session);
        chatService.delete(userId, conversationId);
        return ResponseEntity.noContent().build();
    }
}

package com.biorag.platform.chat.service;

import com.biorag.platform.auth.entity.UserAccount;
import com.biorag.platform.auth.exception.UnauthenticatedException;
import com.biorag.platform.auth.repository.UserAccountRepository;
import com.biorag.platform.chat.dto.ChatMessageResponse;
import com.biorag.platform.chat.dto.ChatTurnResponse;
import com.biorag.platform.chat.dto.ConversationResponse;
import com.biorag.platform.chat.dto.CreateConversationRequest;
import com.biorag.platform.chat.entity.ChatConversation;
import com.biorag.platform.chat.entity.ChatMessage;
import com.biorag.platform.chat.exception.ConversationNotFoundException;
import com.biorag.platform.chat.repository.ChatConversationRepository;
import com.biorag.platform.chat.repository.ChatMessageRepository;
import com.biorag.platform.integration.ai.AiAnswerRequest;
import com.biorag.platform.integration.ai.AiAnswerResponse;
import com.biorag.platform.integration.ai.AiCitationResponse;
import com.biorag.platform.integration.ai.AiHistoryMessage;
import com.biorag.platform.integration.ai.AiServiceClient;
import com.biorag.platform.knowledgebase.entity.KnowledgeBase;
import com.biorag.platform.knowledgebase.service.KnowledgeBaseService;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.Collections;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 会话业务服务，负责持久化消息、组装历史并调用 Python。
 */
@Service
public class ChatService {

    private final ChatConversationRepository conversationRepository;
    private final ChatMessageRepository messageRepository;
    private final UserAccountRepository userAccountRepository;
    private final KnowledgeBaseService knowledgeBaseService;
    private final AiServiceClient aiServiceClient;
    private final ObjectMapper objectMapper;

    /** 注入会话持久化、权限和 AI 调用依赖。 */
    public ChatService(
            ChatConversationRepository conversationRepository,
            ChatMessageRepository messageRepository,
            UserAccountRepository userAccountRepository,
            KnowledgeBaseService knowledgeBaseService,
            AiServiceClient aiServiceClient,
            ObjectMapper objectMapper) {
        this.conversationRepository = conversationRepository;
        this.messageRepository = messageRepository;
        this.userAccountRepository = userAccountRepository;
        this.knowledgeBaseService = knowledgeBaseService;
        this.aiServiceClient = aiServiceClient;
        this.objectMapper = objectMapper;
    }

    /** 为当前登录用户创建一个可持久化的新会话。 */
    @Transactional
    public ConversationResponse create(UUID currentUserId, CreateConversationRequest request) {
        UserAccount owner = userAccountRepository.findById(currentUserId)
                .orElseThrow(UnauthenticatedException::new);
        Set<KnowledgeBase> knowledgeBases = request.resolvedKnowledgeBaseIds().stream()
                .map(knowledgeBaseId -> knowledgeBaseService.requireAccessibleEntity(
                        currentUserId,
                        knowledgeBaseId))
                .collect(java.util.stream.Collectors.toCollection(LinkedHashSet::new));
        String title = request.title() == null || request.title().isBlank()
                ? "新对话"
                : request.title().strip();
        return toConversationResponse(
                conversationRepository.save(new ChatConversation(owner, knowledgeBases, title)));
    }

    /** 查询当前用户的全部会话摘要。 */
    @Transactional(readOnly = true)
    public List<ConversationResponse> list(UUID currentUserId) {
        return conversationRepository.findAllByOwner_IdOrderByUpdatedAtDesc(currentUserId).stream()
                .map(this::toConversationResponse)
                .toList();
    }

    /** 查询指定会话的全部历史消息。 */
    @Transactional(readOnly = true)
    public List<ChatMessageResponse> listMessages(UUID currentUserId, UUID conversationId) {
        requireConversation(currentUserId, conversationId);
        return messageRepository.findAllByConversation_IdOrderByCreatedAtAsc(conversationId).stream()
                .map(this::toMessageResponse)
                .toList();
    }

    /** 保存用户问题，携带最近历史调用 Python，并保存助手回答。 */
    @Transactional
    public ChatTurnResponse sendMessage(
            UUID currentUserId,
            UUID conversationId,
            String content) {
        ChatConversation conversation = requireConversation(currentUserId, conversationId);
        conversation.getKnowledgeBases().forEach(knowledgeBase ->
                knowledgeBaseService.requireAccessibleEntity(currentUserId, knowledgeBase.getId()));
        List<AiHistoryMessage> history = recentHistory(conversationId);
        String question = content.strip();
        ChatMessage userMessage = messageRepository.save(ChatMessage.user(conversation, question));
        List<UUID> knowledgeBaseIds = conversation.getKnowledgeBases().stream()
                .map(KnowledgeBase::getId)
                .toList();
        AiAnswerResponse aiAnswer = aiServiceClient.answer(
                new AiAnswerRequest(question, 5, knowledgeBaseIds, history));
        ChatMessage assistantMessage = messageRepository.save(ChatMessage.assistant(
                conversation,
                aiAnswer.answer(),
                aiAnswer.answerMode(),
                aiAnswer.notice(),
                aiAnswer.knowledgeBaseScore(),
                writeCitations(aiAnswer.citations())));
        conversation.acceptUserQuestion(question);
        conversationRepository.save(conversation);
        return new ChatTurnResponse(
                toConversationResponse(conversation),
                toMessageResponse(userMessage),
                toMessageResponse(assistantMessage),
                aiAnswer.standaloneQuestion());
    }

    /** 删除当前用户拥有的会话及其消息。 */
    @Transactional
    public void delete(UUID currentUserId, UUID conversationId) {
        conversationRepository.delete(requireConversation(currentUserId, conversationId));
    }

    /** 加载最近十二条消息并恢复为从旧到新的顺序。 */
    private List<AiHistoryMessage> recentHistory(UUID conversationId) {
        List<ChatMessage> recent = new ArrayList<>(
                messageRepository.findTop12ByConversation_IdOrderByCreatedAtDesc(conversationId));
        Collections.reverse(recent);
        return recent.stream()
                .map(message -> new AiHistoryMessage(
                        message.getRole().name().toLowerCase(),
                        message.getContent()))
                .toList();
    }

    /** 按所有者加载会话，避免用户猜测 ID 越权访问。 */
    private ChatConversation requireConversation(UUID currentUserId, UUID conversationId) {
        return conversationRepository.findByIdAndOwner_Id(conversationId, currentUserId)
                .orElseThrow(() -> new ConversationNotFoundException(conversationId));
    }

    /** 将会话实体转换为网页摘要。 */
    private ConversationResponse toConversationResponse(ChatConversation conversation) {
        List<KnowledgeBase> knowledgeBases = conversation.getKnowledgeBases().stream()
                .sorted(Comparator.comparing(KnowledgeBase::getName)
                        .thenComparing(KnowledgeBase::getId))
                .toList();
        KnowledgeBase first = knowledgeBases.isEmpty() ? null : knowledgeBases.getFirst();
        List<String> names = knowledgeBases.stream().map(KnowledgeBase::getName).toList();
        return new ConversationResponse(
                conversation.getId(),
                conversation.getTitle(),
                first == null ? null : first.getId(),
                names.isEmpty() ? "内置知识库" : String.join("、", names),
                knowledgeBases.stream().map(KnowledgeBase::getId).toList(),
                names,
                conversation.getCreatedAt(),
                conversation.getUpdatedAt());
    }

    /** 将消息实体及引用 JSON 转换为网页响应。 */
    private ChatMessageResponse toMessageResponse(ChatMessage message) {
        return new ChatMessageResponse(
                message.getId(),
                message.getRole().name().toLowerCase(),
                message.getContent(),
                message.getAnswerMode(),
                message.getNotice(),
                message.getKnowledgeBaseScore(),
                readCitations(message.getCitationsJson()),
                message.getCreatedAt());
    }

    /** 将 Python 引用列表序列化为不可变的消息快照。 */
    private String writeCitations(List<AiCitationResponse> citations) {
        try {
            return objectMapper.writeValueAsString(citations == null ? List.of() : citations);
        } catch (JsonProcessingException exception) {
            throw new IllegalStateException("无法保存回答引用", exception);
        }
    }

    /** 从消息记录恢复引用列表。 */
    private List<AiCitationResponse> readCitations(String citationsJson) {
        try {
            return objectMapper.readValue(
                    citationsJson,
                    new TypeReference<List<AiCitationResponse>>() { });
        } catch (JsonProcessingException exception) {
            throw new IllegalStateException("无法读取回答引用", exception);
        }
    }
}

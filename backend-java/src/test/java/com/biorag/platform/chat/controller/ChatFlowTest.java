package com.biorag.platform.chat.controller;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.http.MediaType.APPLICATION_JSON;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.biorag.platform.auth.repository.UserAccountRepository;
import com.biorag.platform.chat.repository.ChatConversationRepository;
import com.biorag.platform.chat.repository.ChatMessageRepository;
import com.biorag.platform.integration.ai.AiAnswerRequest;
import com.biorag.platform.integration.ai.AiAnswerResponse;
import com.biorag.platform.integration.ai.AiCitationResponse;
import com.biorag.platform.integration.ai.AiServiceClient;
import com.biorag.platform.knowledgebase.repository.KnowledgeBaseRepository;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.mock.web.MockHttpSession;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;

/**
 * 验证网页到 Java 会话持久化及历史传递的完整流程。
 */
@SpringBootTest(properties = "debug=false")
@AutoConfigureMockMvc
@ActiveProfiles("test")
class ChatFlowTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @Autowired
    private ChatMessageRepository messageRepository;

    @Autowired
    private ChatConversationRepository conversationRepository;

    @Autowired
    private KnowledgeBaseRepository knowledgeBaseRepository;

    @Autowired
    private UserAccountRepository userAccountRepository;

    @MockitoBean
    private AiServiceClient aiServiceClient;

    /** 清理有外键关系的业务数据。 */
    @BeforeEach
    void cleanDatabase() {
        messageRepository.deleteAll();
        conversationRepository.deleteAll();
        knowledgeBaseRepository.deleteAll();
        userAccountRepository.deleteAll();
    }

    /** 第二次追问时，Java 应把第一轮问答作为历史传给 Python。 */
    @Test
    void persistsConversationAndPassesHistoryToPython() throws Exception {
        MockHttpSession session = registerAndLogin("chat@example.com");
        when(aiServiceClient.answer(any())).thenReturn(
                answer("RNA-seq 是转录组测序分析流程。", "RNA-seq 是什么？"),
                answer("RNA-seq 通常包括质控、比对和定量。", "RNA-seq 包括哪些步骤？"));

        MvcResult createResult = mockMvc.perform(post("/api/conversations")
                        .session(session)
                        .contentType(APPLICATION_JSON)
                        .content("{}"))
                .andExpect(status().isCreated())
                .andReturn();
        UUID conversationId = responseId(createResult);

        send(session, conversationId, "RNA-seq 是什么？")
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.assistantMessage.citations[0].evidenceId").value("E1"))
                .andExpect(jsonPath("$.data.assistantMessage.citations[0].sourceId").value("source"));
        send(session, conversationId, "它包括哪些步骤？")
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.standaloneQuestion")
                        .value("RNA-seq 包括哪些步骤？"));

        ArgumentCaptor<AiAnswerRequest> captor = ArgumentCaptor.forClass(AiAnswerRequest.class);
        verify(aiServiceClient, org.mockito.Mockito.times(2)).answer(captor.capture());
        List<AiAnswerRequest> requests = captor.getAllValues();
        org.assertj.core.api.Assertions.assertThat(requests.get(0).history()).isEmpty();
        org.assertj.core.api.Assertions.assertThat(requests.get(1).history())
                .extracting(item -> item.role() + ":" + item.content())
                .containsExactly(
                        "user:RNA-seq 是什么？",
                        "assistant:RNA-seq 是转录组测序分析流程。");

        mockMvc.perform(get("/api/conversations/{id}/messages", conversationId).session(session))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.length()").value(4));
    }

    /** 向指定会话发送 JSON 问题。 */
    private org.springframework.test.web.servlet.ResultActions send(
            MockHttpSession session,
            UUID conversationId,
            String content) throws Exception {
        return mockMvc.perform(post("/api/conversations/{id}/messages", conversationId)
                .session(session)
                .contentType(APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(java.util.Map.of("content", content))));
    }

    /** 创建不带引用的测试 AI 回答。 */
    private AiAnswerResponse answer(String content, String standaloneQuestion) {
        return new AiAnswerResponse(
                standaloneQuestion,
                standaloneQuestion,
                content,
                false,
                List.of(new AiCitationResponse(
                        "E1", "chunk-1", 0.9, "source", "source.md", "Overview", null, List.of())),
                "general_knowledge",
                "知识库未检索到精确信息",
                0.2);
    }

    /** 注册并登录测试用户，返回带身份的 Session。 */
    private MockHttpSession registerAndLogin(String email) throws Exception {
        mockMvc.perform(post("/api/auth/register")
                        .contentType(APPLICATION_JSON)
                        .content("""
                                {"email":"%s","password":"secret123"}
                                """.formatted(email)))
                .andExpect(status().isCreated());
        MvcResult loginResult = mockMvc.perform(post("/api/auth/login")
                        .contentType(APPLICATION_JSON)
                        .content("""
                                {"email":"%s","password":"secret123"}
                                """.formatted(email)))
                .andExpect(status().isOk())
                .andReturn();
        return (MockHttpSession) loginResult.getRequest().getSession(false);
    }

    /** 从统一响应中读取新建会话 ID。 */
    private UUID responseId(MvcResult result) throws Exception {
        JsonNode root = objectMapper.readTree(result.getResponse().getContentAsByteArray());
        return UUID.fromString(root.path("data").path("id").asText());
    }
}

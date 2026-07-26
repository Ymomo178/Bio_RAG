package com.biorag.platform.knowledgebase.controller;

import static org.springframework.http.MediaType.APPLICATION_JSON;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.biorag.platform.auth.repository.UserAccountRepository;
import com.biorag.platform.knowledgebase.repository.KnowledgeBaseRepository;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.mock.web.MockHttpSession;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;

/**
 * 注册、登录和知识库所有权的完整流程集成测试。
 */
@SpringBootTest(properties = "debug=false")
@AutoConfigureMockMvc
@ActiveProfiles("test")
class KnowledgeBaseFlowTest {

    private static final String PASSWORD = "secret123";

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @Autowired
    private KnowledgeBaseRepository knowledgeBaseRepository;

    @Autowired
    private UserAccountRepository userAccountRepository;

    /**
     * 按照外键依赖顺序清理测试数据。
     */
    @BeforeEach
    void cleanDatabase() {
        knowledgeBaseRepository.deleteAll();
        userAccountRepository.deleteAll();
    }

    /**
     * 验证未登录用户不能创建知识库。
     */
    @Test
    void rejectsUnauthenticatedCreate() throws Exception {
        mockMvc.perform(post("/api/knowledge-bases")
                        .contentType(APPLICATION_JSON)
                        .content("""
                                {"name":"RNA-seq 知识库"}
                                """))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.error.code").value("UNAUTHENTICATED"));
    }

    /**
     * 串联验证注册、登录、创建、列表、详情、更新和删除流程。
     */
    @Test
    void completesOwnerCrudFlow() throws Exception {
        String email = "owner@example.com";
        MockHttpSession ownerSession = registerAndLogin(email);
        UUID ownerId = userAccountRepository.findByEmail(email).orElseThrow().getId();

        MvcResult createResult = mockMvc.perform(post("/api/knowledge-bases")
                        .session(ownerSession)
                        .contentType(APPLICATION_JSON)
                        .content("""
                                {
                                  "name":" RNA-seq 知识库 ",
                                  "description":" 分析流程和质控规范 ",
                                  "visibility":"PRIVATE",
                                  "ownerId":"00000000-0000-0000-0000-000000000000"
                                }
                                """))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.data.name").value("RNA-seq 知识库"))
                .andExpect(jsonPath("$.data.ownerId").value(ownerId.toString()))
                .andReturn();

        UUID knowledgeBaseId = responseId(createResult);

        mockMvc.perform(get("/api/knowledge-bases").session(ownerSession))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.length()").value(1))
                .andExpect(jsonPath("$.data[0].id").value(knowledgeBaseId.toString()));

        mockMvc.perform(get("/api/knowledge-bases/{id}", knowledgeBaseId).session(ownerSession))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.description").value("分析流程和质控规范"));

        mockMvc.perform(put("/api/knowledge-bases/{id}", knowledgeBaseId)
                        .session(ownerSession)
                        .contentType(APPLICATION_JSON)
                        .content("""
                                {
                                  "name":"RNA-seq 标准知识库",
                                  "description":"更新后的规范",
                                  "visibility":"PUBLIC"
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.name").value("RNA-seq 标准知识库"))
                .andExpect(jsonPath("$.data.visibility").value("PUBLIC"));

        mockMvc.perform(delete("/api/knowledge-bases/{id}", knowledgeBaseId).session(ownerSession))
                .andExpect(status().isNoContent());

        mockMvc.perform(get("/api/knowledge-bases/{id}", knowledgeBaseId).session(ownerSession))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.error.code").value("KNOWLEDGE_BASE_NOT_FOUND"));
    }

    /**
     * 验证私有知识库不可被其他用户读取、修改或删除。
     */
    @Test
    void protectsPrivateKnowledgeBaseOwnership() throws Exception {
        MockHttpSession ownerSession = registerAndLogin("owner@example.com");
        MockHttpSession otherSession = registerAndLogin("other@example.com");
        UUID knowledgeBaseId = createKnowledgeBase(ownerSession, "PRIVATE");

        mockMvc.perform(get("/api/knowledge-bases/{id}", knowledgeBaseId).session(otherSession))
                .andExpect(status().isForbidden());

        mockMvc.perform(delete("/api/knowledge-bases/{id}", knowledgeBaseId).session(otherSession))
                .andExpect(status().isForbidden());
    }

    /**
     * 验证公开知识库可以被其他登录用户读取，但不能被其删除。
     */
    @Test
    void allowsPublicReadButKeepsOwnerWritePermission() throws Exception {
        MockHttpSession ownerSession = registerAndLogin("owner@example.com");
        MockHttpSession otherSession = registerAndLogin("other@example.com");
        UUID knowledgeBaseId = createKnowledgeBase(ownerSession, "PUBLIC");

        mockMvc.perform(get("/api/knowledge-bases/{id}", knowledgeBaseId).session(otherSession))
                .andExpect(status().isOk());

        mockMvc.perform(delete("/api/knowledge-bases/{id}", knowledgeBaseId).session(otherSession))
                .andExpect(status().isForbidden());

        mockMvc.perform(get("/api/knowledge-bases").session(otherSession))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.length()").value(1))
                .andExpect(jsonPath("$.data[0].visibility").value("PUBLIC"))
                .andExpect(jsonPath("$.data[0].owned").value(false))
                .andExpect(jsonPath("$.data[0].editable").value(false));
    }

    /**
     * 通过真实注册和登录接口创建带用户身份的测试 Session。
     */
    private MockHttpSession registerAndLogin(String email) throws Exception {
        mockMvc.perform(post("/api/auth/register")
                        .contentType(APPLICATION_JSON)
                        .content("""
                                {"email":"%s","password":"%s"}
                                """.formatted(email, PASSWORD)))
                .andExpect(status().isCreated());

        MvcResult loginResult = mockMvc.perform(post("/api/auth/login")
                        .contentType(APPLICATION_JSON)
                        .content("""
                                {"email":"%s","password":"%s"}
                                """.formatted(email, PASSWORD)))
                .andExpect(status().isOk())
                .andReturn();

        return (MockHttpSession) loginResult.getRequest().getSession(false);
    }

    /**
     * 使用指定 Session 创建知识库并返回生成的知识库 ID。
     */
    private UUID createKnowledgeBase(MockHttpSession session, String visibility) throws Exception {
        MvcResult result = mockMvc.perform(post("/api/knowledge-bases")
                        .session(session)
                        .contentType(APPLICATION_JSON)
                        .content("""
                                {"name":"测试知识库","visibility":"%s"}
                                """.formatted(visibility)))
                .andExpect(status().isCreated())
                .andReturn();
        return responseId(result);
    }

    /**
     * 从统一 JSON 响应中解析业务对象 ID。
     */
    private UUID responseId(MvcResult result) throws Exception {
        JsonNode root = objectMapper.readTree(result.getResponse().getContentAsByteArray());
        return UUID.fromString(root.path("data").path("id").asText());
    }
}

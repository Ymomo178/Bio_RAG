package com.biorag.platform.admin.controller;

import static org.springframework.http.MediaType.APPLICATION_JSON;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.biorag.platform.auth.repository.UserAccountRepository;
import com.biorag.platform.knowledgebase.repository.KnowledgeBaseRepository;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.mock.web.MockHttpSession;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;

/** 验证配置管理员、用户管理入口和内置知识库创建流程。 */
@SpringBootTest(properties = {"debug=false", "app.admin-email=admin@example.com"})
@AutoConfigureMockMvc
@ActiveProfiles("test")
class AdminFlowTest {
    @Autowired private MockMvc mockMvc;
    @Autowired private ObjectMapper mapper;
    @Autowired private KnowledgeBaseRepository knowledgeBases;
    @Autowired private UserAccountRepository users;

    /** 清理本测试创建的外键数据，避免影响其他 Spring 测试上下文。 */
    @AfterEach
    void cleanDatabase() {
        knowledgeBases.deleteAll();
        users.deleteAll();
    }

    /** 配置邮箱登录后应获得管理员角色，并能创建内置知识库和读取用户列表。 */
    @Test
    void configuredAdminCanManageBuiltInKnowledgeBases() throws Exception {
        MockHttpSession session = registerAndLogin("admin@example.com");

        mockMvc.perform(get("/api/admin/users").session(session))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data[0].roles[?(@ == 'ADMIN')]").exists());
        mockMvc.perform(post("/api/knowledge-bases").session(session).contentType(APPLICATION_JSON)
                        .content("{\"name\":\"系统资料\",\"visibility\":\"BUILT_IN\"}"))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.data.visibility").value("BUILT_IN"))
                .andExpect(jsonPath("$.data.editable").value(true));
    }

    /** 停用账号后，其已经建立的 Session 也不能继续访问业务接口。 */
    @Test
    void disablingUserInvalidatesExistingSession() throws Exception {
        MockHttpSession adminSession = registerAndLogin("admin@example.com");
        MockHttpSession userSession = registerAndLogin("member@example.com");
        var user = users.findByEmail("member@example.com").orElseThrow();

        mockMvc.perform(put("/api/admin/users/{id}", user.getId()).session(adminSession)
                        .contentType(APPLICATION_JSON)
                        .content("{\"status\":\"DISABLED\",\"admin\":false}"))
                .andExpect(status().isOk());
        mockMvc.perform(get("/api/knowledge-bases").session(userSession))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.error.code").value("ACCOUNT_DISABLED"));
    }

    /** 注册并登录测试账号。 */
    private MockHttpSession registerAndLogin(String email) throws Exception {
        String body = mapper.writeValueAsString(java.util.Map.of("email", email, "password", "secret123"));
        mockMvc.perform(post("/api/auth/register").contentType(APPLICATION_JSON).content(body))
                .andExpect(status().isCreated());
        MvcResult result = mockMvc.perform(post("/api/auth/login").contentType(APPLICATION_JSON).content(body))
                .andExpect(status().isOk()).andReturn();
        return (MockHttpSession) result.getRequest().getSession(false);
    }
}

package com.biorag.platform.auth.controller;

import static org.springframework.http.MediaType.APPLICATION_JSON;
import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.biorag.platform.auth.entity.UserAccount;
import com.biorag.platform.auth.repository.UserAccountRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.mock.web.MockHttpSession;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;

/**
 * 用户登录接口的集成测试，覆盖成功和主要失败分支。
 */
@SpringBootTest(properties = "debug=false")
@AutoConfigureMockMvc
@ActiveProfiles("test")
class AuthLoginControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private UserAccountRepository userAccountRepository;

    @Autowired
    private PasswordEncoder passwordEncoder;

    /**
     * 每个测试执行前清空用户，避免测试数据互相影响。
     */
    @BeforeEach
    void cleanUsers() {
        userAccountRepository.deleteAll();
    }

    /**
     * 验证正确邮箱和密码可以通过登录校验。
     */
    @Test
    void logsInWithCorrectCredentials() throws Exception {
        createUser("analyst@example.com", "secret123");

        mockMvc.perform(post("/api/auth/login")
                        .contentType(APPLICATION_JSON)
                        .content("""
                                {"email":" ANALYST@example.com ","password":"secret123"}
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data.email").value("analyst@example.com"))
                .andExpect(jsonPath("$.data.status").value("ACTIVE"))
                .andExpect(jsonPath("$.data.id").isNotEmpty());
    }

    /**
     * 验证密码错误时返回统一的凭据错误。
     */
    @Test
    void rejectsWrongPassword() throws Exception {
        createUser("analyst@example.com", "secret123");

        mockMvc.perform(post("/api/auth/login")
                        .contentType(APPLICATION_JSON)
                        .content("""
                                {"email":"analyst@example.com","password":"wrong123"}
                                """))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.error.code").value("INVALID_CREDENTIALS"))
                .andExpect(jsonPath("$.error.message").value("邮箱或密码错误"));
    }

    /**
     * 验证邮箱不存在时也返回统一的凭据错误，避免泄露注册信息。
     */
    @Test
    void rejectsUnknownEmailWithoutRevealingIt() throws Exception {
        mockMvc.perform(post("/api/auth/login")
                        .contentType(APPLICATION_JSON)
                        .content("""
                                {"email":"missing@example.com","password":"secret123"}
                                """))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.error.code").value("INVALID_CREDENTIALS"))
                .andExpect(jsonPath("$.error.message").value("邮箱或密码错误"));
    }

    /**
     * 验证账号停用后即使密码正确也不能登录。
     */
    @Test
    void rejectsDisabledAccount() throws Exception {
        UserAccount user = createUser("disabled@example.com", "secret123");
        user.disable();
        userAccountRepository.saveAndFlush(user);

        mockMvc.perform(post("/api/auth/login")
                        .contentType(APPLICATION_JSON)
                        .content("""
                                {"email":"disabled@example.com","password":"secret123"}
                                """))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.error.code").value("ACCOUNT_DISABLED"));
    }

    /**
     * 验证不符合格式的登录参数会在进入业务层前被拒绝。
     */
    @Test
    void rejectsInvalidLoginRequest() throws Exception {
        mockMvc.perform(post("/api/auth/login")
                        .contentType(APPLICATION_JSON)
                        .content("""
                                {"email":"not-an-email","password":"short"}
                                """))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.code").value("VALIDATION_ERROR"));
    }

    /**
     * 验证退出登录会销毁已经建立的 Session。
     */
    @Test
    void logsOutAndInvalidatesSession() throws Exception {
        createUser("analyst@example.com", "secret123");

        MvcResult loginResult = mockMvc.perform(post("/api/auth/login")
                        .contentType(APPLICATION_JSON)
                        .content("""
                                {"email":"analyst@example.com","password":"secret123"}
                                """))
                .andExpect(status().isOk())
                .andReturn();
        MockHttpSession session = (MockHttpSession) loginResult.getRequest().getSession(false);

        mockMvc.perform(post("/api/auth/logout").session(session))
                .andExpect(status().isNoContent());

        assertThat(session.isInvalid()).isTrue();
    }

    /**
     * 创建带 BCrypt 密码哈希的测试用户。
     */
    private UserAccount createUser(String email, String rawPassword) {
        return userAccountRepository.saveAndFlush(
                new UserAccount(email, passwordEncoder.encode(rawPassword)));
    }
}

package com.biorag.platform;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

/**
 * 应用启动和公共健康接口的集成测试。
 */
@ActiveProfiles("test")
@SpringBootTest(properties = "debug=false")
@AutoConfigureMockMvc
class BioRagApplicationTests {

    @Autowired
    private MockMvc mockMvc;

    /**
     * 验证 Spring 容器能够启动，且健康接口可正常返回。
     */
    @Test
    void contextLoadsAndPublicHealthEndpointResponds() throws Exception {
        mockMvc.perform(get("/api/v1/system/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data.service").value("bio-rag-backend"))
                .andExpect(jsonPath("$.data.status").value("UP"));
    }
}

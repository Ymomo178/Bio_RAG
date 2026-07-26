package com.biorag.platform.integration.ai;

import java.time.Duration;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

/**
 * 封装 Java 到 Python AI 服务的全部 HTTP 调用。
 */
@Component
public class AiServiceClient {

    private final RestClient restClient;

    /**
     * 根据配置创建带连接和读取超时的同步 HTTP 客户端。
     */
    public AiServiceClient(
            @Value("${app.ai-service.base-url}") String baseUrl,
            @Value("${app.ai-service.connect-timeout}") Duration connectTimeout,
            @Value("${app.ai-service.read-timeout}") Duration readTimeout) {
        SimpleClientHttpRequestFactory requestFactory = new SimpleClientHttpRequestFactory();
        requestFactory.setConnectTimeout(connectTimeout);
        requestFactory.setReadTimeout(readTimeout);
        this.restClient = RestClient.builder()
                .baseUrl(baseUrl)
                .requestFactory(requestFactory)
                .build();
    }

    /**
     * 携带最近会话历史调用 Python RAG 问答接口。
     */
    public AiAnswerResponse answer(AiAnswerRequest request) {
        try {
            AiAnswerResponse response = requestAnswer(request);
            if (response == null) {
                throw new IllegalStateException("Python 返回了空响应");
            }
            return response;
        } catch (Exception exception) {
            throw new AiServiceException("AI 回答服务暂时不可用，请稍后重试", exception);
        }
    }

    /** 执行单次 Python 问答请求，供有限次数的瞬时故障重试复用。 */
    private AiAnswerResponse requestAnswer(AiAnswerRequest request) {
        return restClient.post()
                .uri("/api/v1/chat/answers")
                .body(request)
                .retrieve()
                .body(AiAnswerResponse.class);
    }

    /**
     * 通知 Python 解析、切分并索引一份已上传文档。
     */
    public AiDocumentIndexResponse indexDocument(AiDocumentIndexRequest request) {
        try {
            AiDocumentIndexResponse response = restClient.post()
                    .uri("/api/v1/documents/index")
                    .body(request)
                    .retrieve()
                    .body(AiDocumentIndexResponse.class);
            if (response == null) {
                throw new IllegalStateException("Python 返回了空响应");
            }
            return response;
        } catch (Exception exception) {
            throw new AiServiceException("文档已保存，但索引处理失败", exception);
        }
    }
}

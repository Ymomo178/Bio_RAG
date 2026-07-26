package com.biorag.platform;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * Bio RAG Java 后端的启动入口。
 */
@SpringBootApplication
public class BioRagApplication {

    /**
     * 创建 Spring 容器并启动内置 Web 服务器。
     */
    public static void main(String[] args) {
        SpringApplication.run(BioRagApplication.class, args);
    }
}

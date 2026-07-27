# 第一阶段使用 Maven 构建可执行 Spring Boot JAR。
ARG DOCKER_REGISTRY=docker.io
FROM ${DOCKER_REGISTRY}/library/maven:3.9-eclipse-temurin-21 AS build

ARG MAVEN_MIRROR_URL=https://maven.aliyun.com/repository/public
ENV MAVEN_MIRROR_URL=${MAVEN_MIRROR_URL}

WORKDIR /workspace
COPY maven-settings.xml /root/.m2/settings.xml
COPY pom.xml ./
RUN mvn -B -ntp dependency:go-offline

COPY src ./src
RUN mvn -B -ntp -DskipTests package

# 运行阶段只保留 Java 运行时和健康检查工具。
FROM ${DOCKER_REGISTRY}/library/eclipse-temurin:21-jre-jammy

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=build /workspace/target/backend-java-*.jar /app/app.jar
RUN mkdir -p /app/uploads /app/artifacts/uploads /app/data

EXPOSE 8080

HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=10 \
    CMD curl --fail --silent http://127.0.0.1:8080/api/v1/system/health >/dev/null || exit 1

ENTRYPOINT ["java", "-jar", "/app/app.jar"]

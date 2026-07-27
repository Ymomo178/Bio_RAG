# Node 阶段负责编译 React 静态资源。
ARG DOCKER_REGISTRY=docker.io
FROM ${DOCKER_REGISTRY}/library/node:22-alpine AS build

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

COPY index.html tsconfig.json tsconfig.app.json tsconfig.node.json vite.config.ts ./
COPY src ./src
RUN npm run build

# Nginx 提供网页，并把 /api 请求转发给 Java 后端。
FROM ${DOCKER_REGISTRY}/library/nginx:alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=10 \
    CMD wget --quiet --tries=1 --spider http://127.0.0.1/health || exit 1

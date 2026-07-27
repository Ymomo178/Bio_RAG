# Bio RAG

Bio RAG 是一个面向生物信息学文档问答的全栈 RAG 项目。系统支持用户上传文档、建立知识库、进行多轮问答，并返回带来源引用和原图的回答。

当前版本是本地可运行的 MVP，已经打通：

- React + Vite 网页端
- Spring Boot Java 业务后端
- FastAPI Python AI 服务
- PostgreSQL + pgvector
- 文档解析、切分、向量化和混合检索
- BGE-M3 embedding、关键词检索、Reranker
- OpenAI 兼容格式 LLM 调用，目前按 Qwen 配置
- 用户注册登录、会话记忆、知识库权限、管理员管理
- 文档图片提取、图片清单、引用关联原图展示

## 项目结构

```text
Bio_RAG/
├── backend-java/        # Spring Boot 后端：用户、权限、知识库、文档、会话
├── ai-service-python/   # FastAPI AI 服务：文档处理、检索、重排、LLM 生成
├── web/                 # React + Vite 前端
├── infra/               # 基础设施脚本，目前包含 pgvector 初始化 SQL
├── data/                # 评测集和数据源配置；原始数据与向量索引不提交
├── reports/             # 检索评测结果
├── docker-compose.yml   # 源码构建版 Docker Compose：Web、Java、Python、PostgreSQL
├── docker-compose.images.yml # 预构建镜像版 Docker Compose
└── docker-compose.gpu.yml # NVIDIA GPU 推理覆盖配置
```

## 功能状态

已完成：

- 用户注册、登录、退出和 Session 鉴权
- 普通用户与管理员角色
- 私有、公开、内置知识库
- 多知识库选择问答
- 文档上传和索引入库
- 多轮会话和上下文改写
- RAG 检索、Reranker 和 Qwen 生成
- 引用来源、章节、页码和关联图片展示
- 无答案兜底和基础评测集
- Docker Compose 一键启动四服务
- GitHub Actions 发布 GHCR 预构建镜像

尚未完成：

- 一键初始化内置知识库
- GitHub Actions 自动测试
- 生产级部署配置

## Docker 启动

推荐优先使用 Docker。浏览器只需要访问 Web 容器，Web 会把 `/api` 请求转发给 Java，Java 再调用 Python AI 服务。

### 1. 准备配置

```powershell
Copy-Item .env.example .env
```

至少填写：

```env
LLM_PROVIDER=qwen
LLM_BASE_URL=你的 OpenAI 兼容接口地址
LLM_API_KEY=你的 API Key
LLM_MODEL=你的模型名
APP_ADMIN_EMAIL=你的管理员邮箱
```

不要提交 `.env`。

数据库配置分为容器和宿主机两组，不能混用地址：

- `POSTGRES_DB`、`POSTGRES_USER`、`POSTGRES_PASSWORD` 创建 Docker 中的 PostgreSQL。
- 在宿主机运行 Java 时，`DB_URL` 必须使用 `localhost`，并让 `DB_USERNAME`、`DB_PASSWORD` 与上面的容器账号一致。
- 在宿主机运行 Python 时，`AI_DATABASE_URL` 同样使用 `host=localhost`，账号密码也要一致。
- Compose 会在容器内自动改用服务名 `postgres`，因此不要把 `.env` 中的宿主机地址手动改成 `postgres`。

示例中的 `biorag_dev` 只适合本地开发。部署到共享或公网环境时应更换数据库密码，并在 HTTPS 入口下设置 `SESSION_COOKIE_SECURE=true`；本地 `http://localhost:5173` 保持 `false`。

容器启动时会校验 `LLM_BASE_URL`、`LLM_API_KEY`、`LLM_MODEL` 和 `APP_ADMIN_EMAIL`。缺少配置时服务会直接终止并在容器日志中指出缺少的变量，避免运行到第一次请求才失败。

### 2. 使用预构建镜像启动

不想在本机编译 Java、Node、Python 和 PyTorch 依赖时，使用 GHCR 镜像版 Compose：

```powershell
docker compose -f docker-compose.images.yml up -d
```

NVIDIA GPU 模式：

```powershell
docker compose -f docker-compose.images.yml -f docker-compose.gpu.yml up -d
```

如果拉取 GHCR 镜像时提示无权限，需要先在 GitHub Packages 中把三个容器包设为公开，或登录 GHCR 后再拉取。
默认使用 `latest` 并在启动时重新拉取；需要可重复部署时，在 `.env` 的 `WEB_IMAGE`、`BACKEND_IMAGE`、`AI_SERVICE_IMAGE` 中固定版本标签。

### 3. 本地源码构建启动

如果正在开发代码，使用源码构建版 Compose：

```powershell
docker compose up -d --build
```

### 4. 本地源码构建 + NVIDIA GPU

已经安装 NVIDIA Container Toolkit 或 Docker Desktop GPU 支持时使用：

```powershell
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build
```

### 5. 访问地址

```text
网页入口：http://localhost:5173
Java 后端：http://localhost:8080
Python AI：http://localhost:8000
PostgreSQL：localhost:5432
```

常用命令：

```powershell
docker compose ps
docker compose logs -f backend-java
docker compose logs -f ai-service
docker compose down
```

说明：

- 首次构建会下载 Java、Node、Python、PyTorch 等基础依赖，耗时较长。
- 首次问答或首次上传文档会下载 BGE-M3 和 Reranker 模型，模型缓存保存在 Docker 卷 `model_cache`。
- 默认镜像源使用 `docker.m.daocloud.io`，网络正常时可在 `.env` 中设置 `DOCKER_REGISTRY=docker.io`。
- 预构建镜像由 `.github/workflows/docker-publish.yml` 在 `main` 分支和 `v*.*.*` 标签推送时发布。
- Web 容器已经设置 CSP、防 MIME 嗅探和禁止被页面嵌套等安全响应头。HSTS 必须由实际提供 HTTPS 的网关或反向代理添加，不能在本地 HTTP 容器中强制开启。
- `MAX_CONCURRENT_RETRIEVALS` 和 `MAX_CONCURRENT_GENERATIONS` 分别控制本地模型和远程 LLM 并发。文档索引另有独立锁，但仍占用一个检索槽；CPU 默认允许两个槽，GPU 覆盖配置对 6 GB 显存保守限制为一个，可通过 `GPU_MAX_CONCURRENT_RETRIEVALS` 调整。

## 本地开发启动

### 1. 准备环境

如果要分别调试 Java、Python 或前端，可以使用本地开发模式。需要：

- Java 21
- Python 3.12
- Node.js 20+
- Docker Desktop，用于启动 PostgreSQL + pgvector

复制环境变量示例：

```powershell
Copy-Item .env.example .env
```

然后在 `.env` 中填写：

```env
LLM_PROVIDER=qwen
LLM_BASE_URL=你的 OpenAI 兼容接口地址
LLM_API_KEY=你的 API Key
LLM_MODEL=你的模型名
APP_ADMIN_EMAIL=你的管理员邮箱
```

本地进程通过 `localhost:${POSTGRES_PORT}` 访问数据库。确认 `DB_USERNAME`、`DB_PASSWORD` 以及 `AI_DATABASE_URL` 中的账号密码与 `POSTGRES_USER`、`POSTGRES_PASSWORD` 相同；`postgres` 这个主机名只在 Compose 网络内可用。

### 2. 启动数据库

```powershell
docker compose up -d postgres
```

### 3. 启动 Java 后端

```powershell
cd backend-java
.\mvnw.cmd spring-boot:run
```

后端默认地址：

```text
http://127.0.0.1:8080
```

### 4. 启动 Python AI 服务

```powershell
cd ai-service-python
.\.venv\Scripts\biorag-api.exe
```

Python 服务默认地址：

```text
http://127.0.0.1:8000
```

### 5. 启动前端

```powershell
cd web
npm install
npm run dev
```

网页入口：

```text
http://127.0.0.1:5173
```

## 测试

Java：

```powershell
cd backend-java
.\mvnw.cmd test
```

Python：

```powershell
cd ai-service-python
.\.venv\Scripts\python.exe -m pytest -q
```

前端：

```powershell
cd web
npm run build
```

当前基线：

- Java：22 tests passed
- Python：49 tests passed
- Web：production build passed

## 数据说明

仓库只提交代码、配置模板、评测集和评测报告。以下内容不会提交：

- `data/raw/`
- `data/normalized/`
- `data/chunks/`
- `data/indexes/`
- `uploads/`
- `artifacts/`
- `.env`
- 本地模型文件

这意味着别人克隆仓库后，需要重新准备数据或等待后续的一键初始化脚本。

## 下一步

计划中的工程化工作：

1. 增加内置知识库初始化流程
2. 增加 GitHub Actions 自动测试
3. 整理发布版本 `v0.1.0`

## 免责声明

本项目用于生物信息学文档检索和辅助问答。模型回答可能存在错误，涉及实验设计、临床医学或高风险决策时，应以原始文献、官方文档和专业人员判断为准。

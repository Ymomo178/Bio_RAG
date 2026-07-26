"""Bio-RAG Python 查询服务，负责数据库检索和 Reranker。"""

import os
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import UUID

from biorag.config import load_project_environment


def create_app(
    retriever: Any | None = None,
    store: Any | None = None,
    llm: Any | None = None,
) -> Any:
    """创建 FastAPI 应用；测试时可注入假的检索器和 LLM。"""
    load_project_environment()
    try:
        from fastapi import FastAPI, HTTPException
        from pydantic import BaseModel, Field
    except ImportError as error:
        raise RuntimeError("请安装服务依赖：pip install -e '.[service]'") from error

    class SearchRequest(BaseModel):
        """定义检索接口的用户问题和知识库范围。"""

        question: str = Field(min_length=1, max_length=4000)
        top_k: int = Field(default=5, ge=1, le=20)
        knowledge_base_ids: list[UUID] | None = Field(default=None, max_length=20)
        knowledge_base_id: UUID | None = None

        def resolved_knowledge_base_ids(self) -> list[UUID] | None:
            """合并新版多选字段和旧版单选字段。"""
            if self.knowledge_base_ids is None and self.knowledge_base_id is None:
                return None
            return list(dict.fromkeys([*(self.knowledge_base_ids or []), *(
                [self.knowledge_base_id] if self.knowledge_base_id else []
            )]))

    class SearchHit(BaseModel):
        """定义返回给 Java 和前端的证据字段。"""

        chunk_id: str
        score: float
        source_id: str | None = None
        normalized_path: str | None = None
        section: str | None = None
        page_number: int | None = None
        content: str
        image_ids: list[str] = Field(default_factory=list)

    class SearchResponse(BaseModel):
        """定义一次检索的完整响应。"""

        question: str
        has_evidence: bool
        hits: list[SearchHit]

    class HistoryMessage(BaseModel):
        """定义 Java 传入的一条最近会话历史。"""

        role: str = Field(pattern="^(user|assistant)$")
        content: str = Field(min_length=1, max_length=4000)

    class AnswerRequest(BaseModel):
        """定义完整 RAG 问答接口的请求字段。"""

        question: str = Field(min_length=1, max_length=4000)
        top_k: int = Field(default=5, ge=1, le=10)
        knowledge_base_ids: list[UUID] = Field(default_factory=list, max_length=20)
        knowledge_base_id: UUID | None = None
        history: list[HistoryMessage] = Field(default_factory=list, max_length=12)

        def resolved_knowledge_base_ids(self) -> list[UUID]:
            """合并新版多选字段和旧版单选字段。"""
            return list(dict.fromkeys([*self.knowledge_base_ids, *(
                [self.knowledge_base_id] if self.knowledge_base_id else []
            )]))

    class CitationResponse(BaseModel):
        """定义一条经过程序验证的回答引用。"""

        evidence_id: str
        chunk_id: str
        score: float
        source_id: str | None = None
        normalized_path: str | None = None
        section: str | None = None
        page_number: int | None = None
        image_ids: list[str] = Field(default_factory=list)

    class AnswerResponse(BaseModel):
        """定义返回给 Java 的最终 RAG 回答。"""

        question: str
        standalone_question: str
        answer: str
        has_evidence: bool
        citations: list[CitationResponse]
        answer_mode: str
        notice: str | None = None
        knowledge_base_score: float | None = None

    class DocumentIndexRequest(BaseModel):
        """定义 Java 保存文件后发起的内部索引任务。"""

        knowledge_base_id: UUID
        document_version_id: UUID
        source_path: str = Field(min_length=1, max_length=4096)
        original_filename: str = Field(min_length=1, max_length=255)

    class DocumentIndexResponse(BaseModel):
        """定义单文档完成向量化后的统计信息。"""

        document_version_id: UUID
        chunk_count: int
        image_count: int
        document_title: str

    app = FastAPI(title="Bio-RAG AI Service", version="0.1.0")
    app.state.retriever = retriever
    app.state.store = store
    app.state.llm = llm
    app.state.evidence_threshold = float(os.getenv("MIN_EVIDENCE_SCORE", "0"))
    app.state.retriever_lock = Lock()
    app.state.llm_lock = Lock()
    app.state.inference_lock = Lock()

    def resolve_retriever() -> Any:
        """按需加载 GPU 模型和 PostgreSQL 连接，避免健康检查触发模型加载。"""
        if app.state.retriever is not None:
            return app.state.retriever
        with app.state.retriever_lock:
            if app.state.retriever is not None:
                return app.state.retriever
            from biorag.retrieval.dense import SentenceTransformerEmbedder
            from biorag.retrieval.hybrid import CrossEncoderReranker, HybridSearchConfig
            from biorag.retrieval.postgres import PostgresChunkStore, PostgresHybridRetriever

            connection_string = _database_connection_string()
            app.state.store = PostgresChunkStore(connection_string)
            embedder = SentenceTransformerEmbedder(
                model_name=os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3"),
                device=os.getenv("EMBEDDING_DEVICE", "cuda"),
                batch_size=int(os.getenv("EMBEDDING_BATCH_SIZE", "4")),
            )
            reranker_path = (
                os.getenv("RERANKER_MODEL_PATH")
                or os.getenv("RERANKER_MODEL")
                or "BAAI/bge-reranker-v2-m3"
            )
            reranker = CrossEncoderReranker(
                model_name=reranker_path,
                device=os.getenv("RERANKER_DEVICE", "cuda"),
                batch_size=int(os.getenv("RERANKER_BATCH_SIZE", "2")),
            )
            config = HybridSearchConfig(
                dense_candidate_count=int(os.getenv("DENSE_CANDIDATE_COUNT", "50")),
                keyword_candidate_count=int(os.getenv("KEYWORD_CANDIDATE_COUNT", "50")),
                rerank_candidate_count=int(os.getenv("RERANK_CANDIDATE_COUNT", "100")),
            )
            app.state.retriever = PostgresHybridRetriever(app.state.store, embedder, reranker, config)
        return app.state.retriever

    def resolve_llm() -> Any:
        """按需读取 .env 并创建 OpenAI 兼容的 Qwen 客户端。"""
        if app.state.llm is not None:
            return app.state.llm
        with app.state.llm_lock:
            if app.state.llm is not None:
                return app.state.llm
            from biorag.generation.llm import LlmConfig, OpenAICompatibleLlm

            app.state.llm = OpenAICompatibleLlm(LlmConfig.from_environment())
        return app.state.llm

    @app.get("/health")
    def health() -> dict[str, str]:
        """检查服务进程和数据库连接状态。"""
        if app.state.store is None:
            return {"status": "UP", "database": "NOT_INITIALIZED"}
        try:
            app.state.store.healthcheck()
        except Exception as error:
            raise HTTPException(status_code=503, detail=f"数据库不可用：{error}") from error
        return {"status": "UP", "database": "UP"}

    @app.post("/api/v1/retrieval/search", response_model=SearchResponse)
    def search(request: SearchRequest) -> SearchResponse:
        """执行混合检索和重排序，返回可供 LLM 使用的证据。"""
        try:
            with app.state.inference_lock:
                active_retriever = resolve_retriever()
                results = active_retriever.search(
                    request.question,
                    request.top_k,
                    request.resolved_knowledge_base_ids(),
                )
        except Exception as error:
            raise HTTPException(status_code=503, detail=f"检索服务不可用：{error}") from error
        hits = [
            SearchHit(
                chunk_id=result.chunk_id,
                score=result.score,
                source_id=result.chunk.get("source_id"),
                normalized_path=result.chunk.get("normalized_path"),
                section=result.chunk.get("section"),
                page_number=result.chunk.get("page_number"),
                content=str(result.chunk.get("content", "")),
                image_ids=[str(image_id) for image_id in result.chunk.get("image_ids", [])],
            )
            for result in results
        ]
        has_evidence = bool(hits) and hits[0].score >= app.state.evidence_threshold
        return SearchResponse(question=request.question, has_evidence=has_evidence, hits=hits)

    @app.post("/api/v1/chat/answers", response_model=AnswerResponse)
    def answer(request: AnswerRequest) -> AnswerResponse:
        """执行检索增强生成，并只返回能够映射到真实文本块的引用。"""
        try:
            from biorag.generation.answering import RagAnswerService
            from biorag.generation.llm import ConversationMessage

            with app.state.inference_lock:
                service = RagAnswerService(
                    resolve_retriever(),
                    resolve_llm(),
                    app.state.evidence_threshold,
                )
                result = service.answer(
                    request.question,
                    request.top_k,
                    request.resolved_knowledge_base_ids(),
                    [
                        ConversationMessage(role=item.role, content=item.content)
                        for item in request.history
                    ],
                )
        except Exception as error:
            raise HTTPException(status_code=503, detail=f"回答生成服务不可用：{error}") from error
        citations = [
            CitationResponse(
                evidence_id=citation.evidence_id,
                chunk_id=citation.chunk_id,
                score=citation.score,
                source_id=citation.source_id,
                normalized_path=citation.normalized_path,
                section=citation.section,
                page_number=citation.page_number,
                image_ids=list(citation.image_ids),
            )
            for citation in result.citations
        ]
        return AnswerResponse(
            question=result.question,
            standalone_question=result.standalone_question,
            answer=result.answer,
            has_evidence=result.has_evidence,
            citations=citations,
            answer_mode=result.answer_mode,
            notice=result.notice,
            knowledge_base_score=result.knowledge_base_score,
        )

    @app.post("/api/v1/documents/index", response_model=DocumentIndexResponse)
    def index_document(request: DocumentIndexRequest) -> DocumentIndexResponse:
        """处理 Java 已保存的单个文件，并将文本块写入 pgvector。"""
        try:
            from biorag.ingestion.upload import index_uploaded_document

            with app.state.inference_lock:
                active_retriever = resolve_retriever()
                source_path = _validated_upload_path(request.source_path)
                store = app.state.store or getattr(active_retriever, "store", None)
                embedder = getattr(active_retriever, "embedder", None)
                if store is None or embedder is None:
                    raise RuntimeError("当前检索器不支持文档入库")
                result = index_uploaded_document(
                    source_path=source_path,
                    original_filename=request.original_filename,
                    knowledge_base_id=request.knowledge_base_id,
                    document_version_id=request.document_version_id,
                    artifact_root=_upload_artifact_root(),
                    embedder=embedder,
                    store=store,
                )
        except Exception as error:
            raise HTTPException(status_code=503, detail=f"文档索引服务不可用：{error}") from error
        return DocumentIndexResponse(
            document_version_id=request.document_version_id,
            chunk_count=result.chunk_count,
            image_count=result.image_count,
            document_title=result.document_title,
        )

    return app


def _database_connection_string() -> str:
    """从统一环境变量读取 PostgreSQL 连接字符串。"""
    return os.getenv(
        "AI_DATABASE_URL",
        os.getenv(
            "DATABASE_URL",
            "host=localhost port=5432 dbname=biorag user=biorag password=biorag_dev",
        ),
    )


def _validated_upload_path(raw_path: str) -> Path:
    """只允许 Python 读取统一上传目录内的文件。"""
    upload_root = Path(os.getenv("UPLOAD_ROOT", "../uploads")).resolve()
    source_path = Path(raw_path).resolve()
    if not source_path.is_relative_to(upload_root):
        raise ValueError("上传文件路径超出允许目录")
    if not source_path.is_file():
        raise ValueError("上传文件不存在")
    return source_path


def _upload_artifact_root() -> Path:
    """返回上传文档规范化结果和图片资产目录。"""
    return Path(os.getenv("UPLOAD_ARTIFACT_ROOT", "../artifacts/uploads")).resolve()


def main() -> None:
    """启动 Uvicorn 开发服务。"""
    import uvicorn

    uvicorn.run(
        "biorag.api:create_app",
        factory=True,
        host=os.getenv("AI_SERVICE_HOST", "127.0.0.1"),
        port=int(os.getenv("AI_SERVICE_PORT", "8000")),
    )


if __name__ == "__main__":
    main()

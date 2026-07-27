"""Python 查询接口的请求校验和响应结构测试。"""

from dataclasses import dataclass
from typing import Any

import pytest
from fastapi.testclient import TestClient

from biorag.api import create_app
from biorag.generation.llm import ConversationMessage, EvidenceInput, LlmAnswer
from biorag.retrieval.dense import SearchResult


@dataclass
class FakeRetriever:
    """返回固定证据的假检索器，避免 API 单元测试加载 GPU 模型。"""

    def search(self, query: str, top_k: int, knowledge_base_id: Any = None) -> list[SearchResult]:
        """返回一个带来源和图片的测试文本块。"""
        chunk = {
            "source_id": "fastqc-help",
            "normalized_path": "fastqc-help/report.md",
            "section": "Report",
            "page_number": 3,
            "content": "FastQC report content",
            "image_ids": ["image-001"],
        }
        return [SearchResult("chunk-001", 0.91, chunk)][:top_k]


class FakeLlm:
    """返回固定结构化答案的假 LLM。"""

    def contextualize(
        self,
        question: str,
        history: list[ConversationMessage],
    ) -> str:
        """存在历史时模拟代词消解后的完整问题。"""
        return "RNA-seq 如何进行质量控制？" if history else question

    def generate(
        self,
        question: str,
        evidence: list[EvidenceInput],
        history: list[ConversationMessage] | None = None,
    ) -> LlmAnswer:
        """引用检索结果中的第一条证据。"""
        return LlmAnswer("FastQC 可以生成质量检查报告。", ("E1",))

    def generate_general(
        self,
        question: str,
        history: list[ConversationMessage] | None = None,
    ) -> LlmAnswer:
        """返回不带知识库引用的通用知识回答。"""
        return LlmAnswer("这是通用知识回答。", ())


class FailingRetriever:
    """抛出含敏感文本的异常，用于验证接口不会回显内部信息。"""

    def search(self, *args: Any, **kwargs: Any) -> list[SearchResult]:
        raise RuntimeError("database password=do-not-expose")


def test_search_endpoint_returns_evidence_and_image_ids() -> None:
    """检索接口应返回文本块来源、页码和图片 ID。"""
    client = TestClient(create_app(FakeRetriever(), llm=FakeLlm()))

    response = client.post(
        "/api/v1/retrieval/search",
        json={"question": "FastQC 如何生成报告？", "top_k": 3},
    )

    assert response.status_code == 200
    assert response.json()["has_evidence"] is True
    assert response.json()["hits"][0]["image_ids"] == ["image-001"]


def test_search_endpoint_rejects_empty_question() -> None:
    """空问题必须在请求校验阶段被拒绝。"""
    client = TestClient(create_app(FakeRetriever(), llm=FakeLlm()))

    response = client.post("/api/v1/retrieval/search", json={"question": ""})

    assert response.status_code == 422


def test_search_endpoint_applies_configured_evidence_threshold(monkeypatch) -> None:
    """低于证据阈值的检索结果不能标记为可回答。"""
    monkeypatch.setenv("MIN_EVIDENCE_SCORE", "0.95")
    client = TestClient(create_app(FakeRetriever(), llm=FakeLlm()))

    response = client.post(
        "/api/v1/retrieval/search",
        json={"question": "FastQC", "top_k": 3},
    )

    assert response.status_code == 200
    assert response.json()["has_evidence"] is False
    assert response.json()["hits"]


def test_answer_endpoint_returns_generated_answer_and_verified_citation(monkeypatch) -> None:
    """完整问答接口应返回模型答案和真实文本块引用。"""
    monkeypatch.setenv("MIN_EVIDENCE_SCORE", "0.85")
    client = TestClient(create_app(FakeRetriever(), llm=FakeLlm()))

    response = client.post(
        "/api/v1/chat/answers",
        json={"question": "FastQC 如何生成报告？", "top_k": 3},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["has_evidence"] is True
    assert payload["answer"] == "FastQC 可以生成质量检查报告。"
    assert payload["answer_mode"] == "knowledge_base"
    assert payload["standalone_question"] == "FastQC 如何生成报告？"
    assert payload["notice"] is None
    assert payload["citations"][0]["chunk_id"] == "chunk-001"
    assert payload["citations"][0]["image_ids"] == ["image-001"]


def test_answer_endpoint_marks_general_knowledge_fallback(monkeypatch) -> None:
    """知识库分数不足时接口应返回通用回答和明显提示。"""
    monkeypatch.setenv("MIN_EVIDENCE_SCORE", "0.95")
    client = TestClient(create_app(FakeRetriever(), llm=FakeLlm()))

    response = client.post(
        "/api/v1/chat/answers",
        json={"question": "知识库外的问题", "top_k": 3},
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["has_evidence"] is False
    assert payload["answer_mode"] == "general_knowledge"
    assert payload["notice"]
    assert payload["citations"] == []


def test_answer_endpoint_contextualizes_follow_up_question(monkeypatch) -> None:
    """API 应接收历史，并返回经过指代消解的独立检索问题。"""
    monkeypatch.setenv("MIN_EVIDENCE_SCORE", "0.85")
    client = TestClient(create_app(FakeRetriever(), llm=FakeLlm()))

    response = client.post(
        "/api/v1/chat/answers",
        json={
            "question": "它如何进行质量控制？",
            "history": [{"role": "user", "content": "请介绍 RNA-seq。"}],
        },
    )

    assert response.status_code == 200
    assert response.json()["standalone_question"] == "RNA-seq 如何进行质量控制？"


def test_create_app_validates_llm_configuration_at_startup(monkeypatch) -> None:
    """生产应用应在启动时拒绝缺失的 LLM 配置。"""
    for variable in ("LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL"):
        monkeypatch.setenv(variable, "")

    with pytest.raises(ValueError, match="缺少 LLM 配置"):
        create_app(FakeRetriever())


def test_create_app_validates_database_configuration_at_startup(monkeypatch) -> None:
    """未注入检索器时，应用启动必须具有数据库连接配置。"""
    monkeypatch.setenv("AI_DATABASE_URL", "")
    monkeypatch.setenv("DATABASE_URL", "")

    with pytest.raises(ValueError, match="缺少数据库配置"):
        create_app(llm=FakeLlm())


def test_search_endpoint_does_not_expose_internal_exception_details() -> None:
    """服务异常只返回稳定错误文案，不向调用方泄漏凭据和堆栈细节。"""
    client = TestClient(create_app(FailingRetriever(), llm=FakeLlm()))

    response = client.post(
        "/api/v1/retrieval/search",
        json={"question": "FastQC", "top_k": 3},
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "检索服务暂不可用"}
    assert "do-not-expose" not in response.text


def test_create_app_uses_separate_retrieval_and_generation_locks() -> None:
    """检索和 LLM 不应再被同一个全局推理锁串行化。"""
    app = create_app(FakeRetriever(), llm=FakeLlm())

    assert app.state.retrieval_lock is not app.state.generation_lock
    assert app.state.indexing_lock is not app.state.retrieval_lock
    assert not hasattr(app.state, "inference_lock")


def test_create_app_rejects_invalid_concurrency_limit(monkeypatch) -> None:
    """非正数并发上限应在服务启动时被拒绝。"""
    monkeypatch.setenv("MAX_CONCURRENT_RETRIEVALS", "0")

    with pytest.raises(ValueError, match="MAX_CONCURRENT_RETRIEVALS 必须是正整数"):
        create_app(FakeRetriever(), llm=FakeLlm())

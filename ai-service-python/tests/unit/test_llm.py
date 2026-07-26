"""OpenAI 兼容 LLM 配置和响应解析测试。"""

from types import SimpleNamespace

import pytest

from biorag.generation.llm import (
    ConversationMessage,
    EvidenceInput,
    LlmConfig,
    OpenAICompatibleLlm,
)


class FakeCompletions:
    """模拟 OpenAI SDK 的 chat.completions 端点。"""

    def __init__(self, content: str) -> None:
        """保存测试需要返回的模型文本。"""
        self.content = content
        self.last_request = None

    def create(self, **request):
        """记录请求并返回与 SDK 相同的最小对象结构。"""
        self.last_request = request
        message = SimpleNamespace(content=self.content)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def _client_with_content(content: str):
    """创建带固定模型响应的假 SDK 客户端。"""
    completions = FakeCompletions(content)
    return SimpleNamespace(chat=SimpleNamespace(completions=completions)), completions


def _config() -> LlmConfig:
    """创建不访问网络的测试配置。"""
    return LlmConfig("qwen", "test-key", "https://example.com/v1", "qwen-test")


def test_openai_compatible_llm_parses_answer_and_citations() -> None:
    """合法 JSON 应转换为答案和去重后的引用编号。"""
    client, completions = _client_with_content(
        '{"answer":"FastQC 用于质量检查。","citation_ids":["E1","E1"]}'
    )
    llm = OpenAICompatibleLlm(_config(), client)

    result = llm.generate(
        "FastQC 是什么？",
        [EvidenceInput("E1", "fastqc-help", "Overview", None, "FastQC quality control")],
    )

    assert result.answer == "FastQC 用于质量检查。"
    assert result.citation_ids == ("E1",)
    assert completions.last_request["model"] == "qwen-test"


def test_openai_compatible_llm_rejects_non_json_response() -> None:
    """模型未按约定返回 JSON 时必须失败，不能猜测引用。"""
    client, _ = _client_with_content("普通自然语言回答")
    llm = OpenAICompatibleLlm(_config(), client)

    with pytest.raises(ValueError, match="合法 JSON"):
        llm.generate(
            "问题",
            [EvidenceInput("E1", "guide", None, None, "evidence")],
        )


def test_openai_compatible_llm_generates_general_answer_without_citations() -> None:
    """通用知识模式应允许回答，但 citation_ids 必须为空。"""
    client, completions = _client_with_content(
        '{"answer":"这是通用知识回答。","citation_ids":[]}'
    )
    llm = OpenAICompatibleLlm(_config(), client)

    result = llm.generate_general("知识库外问题")

    assert result.answer == "这是通用知识回答。"
    assert result.citation_ids == ()
    assert "通用知识" in completions.last_request["messages"][0]["content"]


def test_openai_compatible_llm_contextualizes_follow_up_question() -> None:
    """问题改写应解析 standalone_question，并把历史发送给模型。"""
    client, completions = _client_with_content(
        '{"standalone_question":"RNA-seq 的主要步骤是什么？"}'
    )
    llm = OpenAICompatibleLlm(_config(), client)

    result = llm.contextualize(
        "它的主要步骤是什么？",
        [ConversationMessage("user", "请介绍 RNA-seq。")],
    )

    assert result == "RNA-seq 的主要步骤是什么？"
    assert "请介绍 RNA-seq" in completions.last_request["messages"][1]["content"]


def test_llm_config_requires_api_values(monkeypatch) -> None:
    """缺少密钥、地址或模型名称时应在创建客户端前报错。"""
    for variable in ("LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL"):
        monkeypatch.delenv(variable, raising=False)

    with pytest.raises(ValueError, match="缺少 LLM 配置"):
        LlmConfig.from_environment()

"""OpenAI 兼容 LLM 的配置、调用和结构化响应解析。"""

import json
import os
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class LlmConfig:
    """保存调用 Qwen 等 OpenAI 兼容模型所需的配置。"""

    provider: str
    api_key: str
    base_url: str
    model: str
    timeout_seconds: float = 60.0
    max_tokens: int = 1200
    temperature: float = 0.1

    @classmethod
    def from_environment(cls) -> "LlmConfig":
        """读取并校验 LLM 环境变量，避免在请求时才发现配置缺失。"""
        required = {
            "LLM_API_KEY": os.getenv("LLM_API_KEY", "").strip(),
            "LLM_BASE_URL": os.getenv("LLM_BASE_URL", "").strip().rstrip("/"),
            "LLM_MODEL": os.getenv("LLM_MODEL", "").strip(),
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise ValueError(f"缺少 LLM 配置：{', '.join(missing)}")
        timeout_seconds = float(os.getenv("LLM_TIMEOUT_SECONDS", "60"))
        max_tokens = int(os.getenv("LLM_MAX_TOKENS", "1200"))
        temperature = float(os.getenv("LLM_TEMPERATURE", "0.1"))
        if timeout_seconds <= 0 or max_tokens <= 0:
            raise ValueError("LLM_TIMEOUT_SECONDS 和 LLM_MAX_TOKENS 必须大于 0")
        if not 0 <= temperature <= 2:
            raise ValueError("LLM_TEMPERATURE 必须在 0 和 2 之间")
        return cls(
            provider=os.getenv("LLM_PROVIDER", "openai-compatible").strip(),
            api_key=required["LLM_API_KEY"],
            base_url=required["LLM_BASE_URL"],
            model=required["LLM_MODEL"],
            timeout_seconds=timeout_seconds,
            max_tokens=max_tokens,
            temperature=temperature,
        )


@dataclass(frozen=True)
class EvidenceInput:
    """表示发送给 LLM 的一条编号证据。"""

    evidence_id: str
    source_id: str
    section: str | None
    page_number: int | None
    content: str


@dataclass(frozen=True)
class ConversationMessage:
    """表示用于理解当前问题的最近一条会话消息。"""

    role: str
    content: str


@dataclass(frozen=True)
class LlmAnswer:
    """表示 LLM 返回的答案正文和引用证据编号。"""

    answer: str
    citation_ids: tuple[str, ...]


class AnswerGenerator(Protocol):
    """约束问答服务依赖的最小 LLM 接口，便于测试时替换。"""

    def contextualize(
        self,
        question: str,
        history: list[ConversationMessage],
    ) -> str:
        """结合历史把含有代词的追问改写为可独立检索的问题。"""
        ...

    def generate(
        self,
        question: str,
        evidence: list[EvidenceInput],
        history: list[ConversationMessage] | None = None,
    ) -> LlmAnswer:
        """根据用户问题和证据生成带引用编号的回答。"""
        ...

    def generate_general(
        self,
        question: str,
        history: list[ConversationMessage] | None = None,
    ) -> LlmAnswer:
        """在知识库证据不足时使用模型通用知识生成无引用回答。"""
        ...


class OpenAICompatibleLlm:
    """通过 OpenAI Chat Completions 兼容接口调用 Qwen。"""

    def __init__(self, config: LlmConfig, client: Any | None = None) -> None:
        """创建兼容客户端；测试时允许注入假的 SDK 客户端。"""
        self.config = config
        if client is not None:
            self._client = client
            return
        try:
            from openai import OpenAI
        except ImportError as error:
            raise RuntimeError("请安装 OpenAI 兼容客户端：pip install -e '.[service]'") from error
        self._client = OpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout_seconds,
            max_retries=2,
        )

    def contextualize(
        self,
        question: str,
        history: list[ConversationMessage],
    ) -> str:
        """使用最近会话历史消解代词，得到能够独立理解的检索问题。"""
        if not history:
            return question
        content = self._request_content(
            _CONTEXTUALIZE_SYSTEM_PROMPT,
            _build_contextualize_prompt(question, history),
        )
        return _parse_standalone_question(content)

    def generate(
        self,
        question: str,
        evidence: list[EvidenceInput],
        history: list[ConversationMessage] | None = None,
    ) -> LlmAnswer:
        """调用模型并把 JSON 文本解析成受约束的答案对象。"""
        if not evidence:
            raise ValueError("生成回答前必须提供至少一条证据")
        return self._complete(
            _SYSTEM_PROMPT,
            _build_user_prompt(question, evidence, history or []),
        )

    def generate_general(
        self,
        question: str,
        history: list[ConversationMessage] | None = None,
    ) -> LlmAnswer:
        """在明确告知知识库未命中后，使用模型通用知识兜底回答。"""
        return self._complete(
            _GENERAL_SYSTEM_PROMPT,
            _build_general_prompt(question, history or []),
        )

    def _complete(self, system_prompt: str, user_prompt: str) -> LlmAnswer:
        """执行一次兼容 Chat Completions 调用并解析结构化结果。"""
        return _parse_answer(self._request_content(system_prompt, user_prompt))

    def _request_content(self, system_prompt: str, user_prompt: str) -> str:
        """发送一次模型请求并返回非空的原始文本。"""
        completion = self._client.chat.completions.create(
            model=self.config.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )
        content = completion.choices[0].message.content
        if not isinstance(content, str) or not content.strip():
            raise ValueError("LLM 返回了空内容")
        return content


_SYSTEM_PROMPT = """你是 Bio-RAG 生物信息学问答助手。
你只能依据用户消息中提供的知识库证据回答，不得使用未提供的模型记忆补充事实、参数或命令。
如果证据不足以回答，answer 必须明确说明当前知识库证据不足，citation_ids 返回空数组。
回答中的每个重要事实都必须由 citation_ids 中至少一条证据支持。
answer 使用清晰的 Markdown：先直接回答结论，再按需要使用简短小标题、列表、表格和代码块；不要堆砌重复标题。
命令、参数、文件名和代码使用反引号；步骤较多时使用有序列表；不要在正文中伪造引用编号。
只返回一个 JSON 对象，不要返回 Markdown 代码块或额外说明：
{"answer":"中文回答","citation_ids":["E1","E2"]}
引用编号只能使用本次提供的 E1、E2 等编号。"""

_GENERAL_SYSTEM_PROMPT = """你是 Bio-RAG 生物信息学问答助手。
当前知识库没有检索到足够精确的证据，请改用你的通用知识回答用户问题。
必须清楚区分事实与不确定内容；涉及医学诊断、临床决策或高风险结论时提醒用户咨询专业人士。
当前没有可验证的知识库引用，因此 citation_ids 必须返回空数组，不得伪造来源。
answer 使用清晰的 Markdown：先直接回答，再按需要使用简短小标题、列表、表格和代码块；命令和参数使用反引号。
只返回一个 JSON 对象，不要返回 Markdown 代码块或额外说明：
{"answer":"中文回答","citation_ids":[]}"""

_CONTEXTUALIZE_SYSTEM_PROMPT = """你负责把多轮对话中的最后一个用户问题改写成可独立理解、可用于文档检索的问题。
只补充历史中明确出现的对象，不要回答问题，不要增加历史中不存在的事实。
如果当前问题本身已经完整，保持原意和语言。
只返回一个 JSON 对象，不要返回 Markdown：
{"standalone_question":"改写后的完整问题"}"""


_IMAGE_RENDERING_PROMPT = (
    "如果证据正文包含 asset:// 图片引用，前端能够自动显示对应原图。"
    "用户索要图片时，不要声称无法显示图片；应引用包含目标图片的证据，"
    "也不要在 answer 中复制 asset:// 地址。\n"
)
_SYSTEM_PROMPT = _IMAGE_RENDERING_PROMPT + _SYSTEM_PROMPT


def _build_user_prompt(
    question: str,
    evidence: list[EvidenceInput],
    history: list[ConversationMessage],
) -> str:
    """把问题和有限数量的检索证据组装为稳定 Prompt。"""
    sections = [_format_history(history), f"当前用户问题：\n{question}", "知识库证据："]
    for item in evidence:
        location = [f"来源={item.source_id}"]
        if item.section:
            location.append(f"章节={item.section}")
        if item.page_number is not None:
            location.append(f"页码={item.page_number}")
        sections.append(
            f"[{item.evidence_id}] {'；'.join(location)}\n{item.content.strip()}"
        )
    sections.append("请严格按照 system 消息要求返回 JSON。")
    return "\n\n".join(section for section in sections if section)


def _build_general_prompt(question: str, history: list[ConversationMessage]) -> str:
    """为通用知识兜底回答组装有限的会话历史和当前问题。"""
    sections = [_format_history(history), f"当前用户问题：\n{question}"]
    return "\n\n".join(section for section in sections if section)


def _build_contextualize_prompt(
    question: str,
    history: list[ConversationMessage],
) -> str:
    """组装用于指代消解的最近历史和当前追问。"""
    return f"{_format_history(history)}\n\n当前用户问题：\n{question}"


def _format_history(history: list[ConversationMessage]) -> str:
    """限制历史条数和单条长度，避免上下文无限增长。"""
    if not history:
        return ""
    role_names = {"user": "用户", "assistant": "助手"}
    lines = ["最近会话历史："]
    for message in history[-12:]:
        role = role_names.get(message.role, message.role)
        lines.append(f"{role}：{message.content.strip()[:2000]}")
    return "\n".join(lines)


def _parse_answer(content: str) -> LlmAnswer:
    """解析模型 JSON，并拒绝缺少答案或引用数组的响应。"""
    cleaned = content.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        cleaned = "\n".join(lines[1:-1]).strip()
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as error:
        raise ValueError("LLM 没有返回合法 JSON") from error
    if not isinstance(payload, dict):
        raise ValueError("LLM 响应必须是 JSON 对象")
    answer = payload.get("answer")
    citation_ids = payload.get("citation_ids")
    if not isinstance(answer, str) or not answer.strip():
        raise ValueError("LLM 响应缺少 answer")
    if not isinstance(citation_ids, list) or any(not isinstance(item, str) for item in citation_ids):
        raise ValueError("LLM 响应中的 citation_ids 必须是字符串数组")
    return LlmAnswer(answer.strip(), tuple(dict.fromkeys(citation_ids)))


def _parse_standalone_question(content: str) -> str:
    """解析问题改写 JSON，并拒绝空问题。"""
    cleaned = content.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        cleaned = "\n".join(lines[1:-1]).strip()
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as error:
        raise ValueError("LLM 没有返回合法的问题改写 JSON") from error
    question = payload.get("standalone_question") if isinstance(payload, dict) else None
    if not isinstance(question, str) or not question.strip():
        raise ValueError("LLM 问题改写结果为空")
    return question.strip()

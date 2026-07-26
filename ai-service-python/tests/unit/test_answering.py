"""完整 RAG 回答服务的拒答和引用验证测试。"""

from dataclasses import dataclass
from typing import Any

from biorag.generation.answering import RagAnswerService
from biorag.generation.llm import ConversationMessage, EvidenceInput, LlmAnswer
from biorag.retrieval.dense import SearchResult


@dataclass
class FakeRetriever:
    """返回指定最高分的假检索器。"""

    score: float

    def search(self, query: str, top_k: int, knowledge_base_id: Any = None) -> list[SearchResult]:
        """返回一条带真实来源信息的测试证据。"""
        chunk = {
            "source_id": "star-manual",
            "normalized_path": "star-manual/manual.md",
            "section": "Parameters",
            "page_number": 10,
            "content": "STAR parameter evidence",
            "image_ids": ["image-1"],
        }
        return [SearchResult("chunk-1", self.score, chunk)][:top_k]


class FakeGenerator:
    """返回可配置引用编号并记录调用次数。"""

    def __init__(self, citation_ids: tuple[str, ...] = ("E1",)) -> None:
        """保存模型应返回的引用编号。"""
        self.citation_ids = citation_ids
        self.call_count = 0
        self.general_call_count = 0
        self.contextualized_question = "问题"

    def contextualize(
        self,
        question: str,
        history: list[ConversationMessage],
    ) -> str:
        """模拟根据历史得到独立检索问题。"""
        return self.contextualized_question if history else question

    def generate(
        self,
        question: str,
        evidence: list[EvidenceInput],
        history: list[ConversationMessage] | None = None,
    ) -> LlmAnswer:
        """模拟一次结构化 LLM 回答。"""
        self.call_count += 1
        return LlmAnswer("根据证据生成的回答。", self.citation_ids)

    def generate_general(
        self,
        question: str,
        history: list[ConversationMessage] | None = None,
    ) -> LlmAnswer:
        """模拟一次不带知识库引用的通用知识回答。"""
        self.general_call_count += 1
        return LlmAnswer("基于模型通用知识的回答。", ())


def test_answer_service_uses_general_llm_when_evidence_is_below_threshold() -> None:
    """低分证据应切换到通用知识回答并显示来源提示。"""
    generator = FakeGenerator()
    service = RagAnswerService(FakeRetriever(0.7), generator, 0.85)

    result = service.answer("问题")

    assert result.has_evidence is False
    assert result.citations == ()
    assert generator.call_count == 0
    assert generator.general_call_count == 1
    assert result.answer_mode == "general_knowledge"
    assert result.notice is not None
    assert result.knowledge_base_score == 0.7


def test_answer_service_maps_model_evidence_id_to_real_chunk() -> None:
    """合法短编号应映射成真实文本块、页码和图片 ID。"""
    service = RagAnswerService(FakeRetriever(0.95), FakeGenerator(), 0.85)

    result = service.answer("问题")

    assert result.has_evidence is True
    assert result.answer_mode == "knowledge_base"
    assert result.notice is None
    assert result.citations[0].chunk_id == "chunk-1"
    assert result.citations[0].page_number == 10
    assert result.citations[0].image_ids == ("image-1",)


def test_answer_service_falls_back_when_citation_id_is_fabricated() -> None:
    """不存在的证据编号不能伪造成引用，应转为通用知识回答。"""
    generator = FakeGenerator(("E99",))
    service = RagAnswerService(FakeRetriever(0.95), generator, 0.85)

    result = service.answer("问题")

    assert result.has_evidence is False
    assert result.citations == ()
    assert result.answer_mode == "general_knowledge"
    assert generator.general_call_count == 1


def test_image_request_retries_with_original_question_when_rewrite_is_bad() -> None:
    """图片请求的上下文改写失真时，应使用用户原问题重新检索。"""

    class ImageFallbackRetriever:
        """为改写问题返回低分，为原问题返回带图高分证据。"""

        def __init__(self) -> None:
            self.queries: list[tuple[str, int]] = []

        def search(self, query: str, top_k: int, knowledge_base_id: Any = None) -> list[SearchResult]:
            self.queries.append((query, top_k))
            if query == "错误的改写问题":
                return [SearchResult("bad", 0.3, {"content": "irrelevant", "image_ids": []})]
            return [SearchResult("image", 0.92, {
                "source_id": "nfcore-rnaseq-docs",
                "content": "![workflow](asset://workflow-image)",
                "image_ids": ["workflow-image"],
            })]

    generator = FakeGenerator()
    generator.contextualized_question = "错误的改写问题"
    retriever = ImageFallbackRetriever()
    service = RagAnswerService(retriever, generator, 0.85)

    question = "请返回 nf-core/rnaseq 的原始流程图"
    result = service.answer(
        question,
        top_k=5,
        history=[ConversationMessage("user", "请介绍 nf-core/rnaseq")],
    )

    assert retriever.queries == [("错误的改写问题", 10), (question, 10)]
    assert result.answer_mode == "knowledge_base"
    assert result.knowledge_base_score == 0.92
    assert result.citations[0].image_ids == ("workflow-image",)


def test_image_request_adds_retrieved_image_when_model_omits_it() -> None:
    """模型只引用纯文本块时，程序应补充排名最高的带图证据。"""

    class MixedRetriever:
        """依次返回纯文本证据和带图证据。"""

        def search(self, query: str, top_k: int, knowledge_base_id: Any = None) -> list[SearchResult]:
            return [
                SearchResult("text", 0.95, {
                    "source_id": "nfcore-rnaseq-docs",
                    "content": "workflow overview",
                    "image_ids": [],
                }),
                SearchResult("image", 0.91, {
                    "source_id": "nfcore-rnaseq-docs",
                    "content": "![workflow](asset://workflow-image)",
                    "image_ids": ["workflow-image"],
                }),
            ][:top_k]

    service = RagAnswerService(MixedRetriever(), FakeGenerator(("E1",)), 0.85)

    result = service.answer("请把流程图发给我")

    assert [citation.evidence_id for citation in result.citations] == ["E1", "E2"]
    assert result.citations[1].image_ids == ("workflow-image",)


def test_image_request_removes_action_words_for_retrieval() -> None:
    """图片问题带有礼貌和操作词时，应补充精简后的主题查询。"""

    class VerboseImageRetriever:
        """仅对精简后的图片主题查询返回可靠证据。"""

        def __init__(self) -> None:
            self.queries: list[str] = []

        def search(self, query: str, top_k: int, knowledge_base_id: Any = None) -> list[SearchResult]:
            self.queries.append(query)
            if query == "nf-core/rnaseq workflow diagram":
                return [SearchResult("image", 0.9, {
                    "source_id": "nfcore-rnaseq-docs",
                    "content": "![workflow](asset://workflow-image)",
                    "image_ids": ["workflow-image"],
                })]
            return [SearchResult("bad", 0.3, {"content": "irrelevant", "image_ids": []})]

    question = "Please return the original nf-core/rnaseq workflow diagram directly."
    retriever = VerboseImageRetriever()
    service = RagAnswerService(retriever, FakeGenerator(), 0.85)

    result = service.answer(question)

    assert retriever.queries == [question, "nf-core/rnaseq workflow diagram"]
    assert result.answer_mode == "knowledge_base"
    assert result.citations[0].image_ids == ("workflow-image",)


def test_answer_service_uses_contextualized_question_for_retrieval() -> None:
    """含代词的追问应先改写，再使用完整问题检索。"""
    generator = FakeGenerator()
    generator.contextualized_question = "RNA-seq 的主要步骤是什么？"
    retriever = FakeRetriever(0.95)
    service = RagAnswerService(retriever, generator, 0.85)

    result = service.answer(
        "它的主要步骤是什么？",
        history=[ConversationMessage("user", "请介绍 RNA-seq。")],
    )

    assert result.standalone_question == "RNA-seq 的主要步骤是什么？"

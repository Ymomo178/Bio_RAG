"""组合检索、证据阈值、LLM 生成和可验证引用。"""

import re
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from biorag.generation.llm import AnswerGenerator, ConversationMessage, EvidenceInput
from biorag.retrieval.dense import SearchResult

_GENERAL_NOTICE = "知识库未检索到精确信息，以下内容由 Qwen 基于通用知识生成，请结合可靠来源进一步核实。"


_IMAGE_REQUEST_PATTERN = re.compile(
    r"图片|原图|图像|流程图|示意图|截图|插图|照片|"
    r"\b(?:image|figure|diagram|flowchart|screenshot|photo)\b",
    re.IGNORECASE,
)
_IMAGE_QUERY_FILLER_PATTERN = re.compile(
    r"\b(?:please|can|could|would|you|return|show|display|give|send|provide|"
    r"me|the|an?|original|directly)\b|"
    r"请|可以|能否|麻烦|帮我|给我|返回|展示|显示|发给我|提供|一下|原始",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class VerifiedCitation:
    """表示已经映射到真实文本块的回答引用。"""

    evidence_id: str
    chunk_id: str
    score: float
    source_id: str | None
    normalized_path: str | None
    section: str | None
    page_number: int | None
    image_ids: tuple[str, ...]


@dataclass(frozen=True)
class RagAnswer:
    """表示最终可返回给 Java 的 RAG 回答。"""

    question: str
    standalone_question: str
    answer: str
    has_evidence: bool
    citations: tuple[VerifiedCitation, ...]
    answer_mode: str
    notice: str | None
    knowledge_base_score: float | None


class RagAnswerService:
    """执行完整的检索增强生成流程并验证引用。"""

    def __init__(self, retriever: Any, generator: AnswerGenerator, evidence_threshold: float) -> None:
        """注入检索器、LLM 生成器和最低证据分数。"""
        if not 0 <= evidence_threshold <= 1:
            raise ValueError("证据阈值必须在 0 和 1 之间")
        self.retriever = retriever
        self.generator = generator
        self.evidence_threshold = evidence_threshold

    def answer(
        self,
        question: str,
        top_k: int = 5,
        knowledge_base_ids: list[UUID] | None = None,
        history: list[ConversationMessage] | None = None,
    ) -> RagAnswer:
        """根据证据分数路由知识库回答或通用模型兜底回答。"""
        history = history or []
        standalone_question = self.generator.contextualize(question, history)
        image_requested = _is_image_request(question)
        retrieval_top_k = max(top_k, 10) if image_requested else top_k
        results = self.retriever.search(
            standalone_question,
            retrieval_top_k,
            knowledge_base_ids,
        )
        if image_requested and (
            _top_score(results) < self.evidence_threshold or not _has_images(results)
        ):
            for retry_query in _image_retry_queries(question, standalone_question):
                retry_results = self.retriever.search(
                    retry_query,
                    retrieval_top_k,
                    knowledge_base_ids,
                )
                if _should_use_original_results(
                    results,
                    retry_results,
                    self.evidence_threshold,
                ):
                    results = retry_results
                if _top_score(results) >= self.evidence_threshold and _has_images(results):
                    break
        top_score = results[0].score if results else None
        if not results or results[0].score < self.evidence_threshold:
            return self._answer_from_general_knowledge(
                question,
                standalone_question,
                top_score,
                history,
            )

        evidence, result_by_id = _prepare_evidence(results)
        generated = self.generator.generate(question, evidence, history)
        citations = [
            _to_verified_citation(evidence_id, result_by_id[evidence_id])
            for evidence_id in generated.citation_ids
            if evidence_id in result_by_id
        ]
        if image_requested and not any(citation.image_ids for citation in citations):
            image_citation = _first_image_citation(result_by_id)
            if image_citation is not None:
                citations.append(image_citation)
        if not citations:
            return self._answer_from_general_knowledge(
                question,
                standalone_question,
                top_score,
                history,
            )
        return RagAnswer(
            question=question,
            standalone_question=standalone_question,
            answer=generated.answer,
            has_evidence=True,
            citations=tuple(citations),
            answer_mode="knowledge_base",
            notice=None,
            knowledge_base_score=top_score,
        )

    def _answer_from_general_knowledge(
        self,
        question: str,
        standalone_question: str,
        top_score: float | None,
        history: list[ConversationMessage],
    ) -> RagAnswer:
        """调用 LLM 通用知识，并明确标记该回答没有知识库引用。"""
        generated = self.generator.generate_general(question, history)
        return RagAnswer(
            question=question,
            standalone_question=standalone_question,
            answer=generated.answer,
            has_evidence=False,
            citations=(),
            answer_mode="general_knowledge",
            notice=_GENERAL_NOTICE,
            knowledge_base_score=top_score,
        )


def _is_image_request(question: str) -> bool:
    """判断用户是否明确索要图片、流程图或图表。"""
    return bool(_IMAGE_REQUEST_PATTERN.search(question))


def _image_retry_queries(question: str, standalone_question: str) -> list[str]:
    """生成原问题和去除操作词后的图片检索查询，并保持顺序去重。"""
    simplified = _IMAGE_QUERY_FILLER_PATTERN.sub(" ", standalone_question)
    simplified = " ".join(simplified.split()).strip(" ,.!?，。！？")
    return [
        query
        for query in dict.fromkeys((question, simplified))
        if query and query != standalone_question
    ]


def _top_score(results: list[SearchResult]) -> float:
    """返回候选结果的最高分；没有候选时返回负值。"""
    return results[0].score if results else -1.0


def _has_images(results: list[SearchResult]) -> bool:
    """判断候选结果中是否至少有一个关联原图的文本块。"""
    return any(result.chunk.get("image_ids") for result in results)


def _should_use_original_results(
    contextualized: list[SearchResult],
    original: list[SearchResult],
    evidence_threshold: float,
) -> bool:
    """上下文改写失真或漏掉图片时，选择用户原问题的检索结果。"""
    original_is_reliable = _top_score(original) >= evidence_threshold
    if not original_is_reliable:
        return False
    return (
        _top_score(contextualized) < evidence_threshold
        or (not _has_images(contextualized) and _has_images(original))
    )


def _first_image_citation(
    result_by_id: dict[str, SearchResult],
) -> VerifiedCitation | None:
    """从已检索证据中选择排名最高的带图文本块。"""
    for evidence_id, result in result_by_id.items():
        if result.chunk.get("image_ids"):
            return _to_verified_citation(evidence_id, result)
    return None


def _prepare_evidence(
    results: list[SearchResult],
) -> tuple[list[EvidenceInput], dict[str, SearchResult]]:
    """为检索结果分配短编号，并限制发送给模型的单块文本长度。"""
    evidence: list[EvidenceInput] = []
    result_by_id: dict[str, SearchResult] = {}
    for index, result in enumerate(results, start=1):
        evidence_id = f"E{index}"
        chunk = result.chunk
        evidence.append(
            EvidenceInput(
                evidence_id=evidence_id,
                source_id=str(chunk.get("source_id") or "unknown"),
                section=str(chunk["section"]) if chunk.get("section") else None,
                page_number=int(chunk["page_number"]) if chunk.get("page_number") else None,
                content=str(chunk.get("content", ""))[:4000],
            )
        )
        result_by_id[evidence_id] = result
    return evidence, result_by_id


def _to_verified_citation(evidence_id: str, result: SearchResult) -> VerifiedCitation:
    """将模型选择的短编号转换成可信的数据库元数据。"""
    chunk = result.chunk
    return VerifiedCitation(
        evidence_id=evidence_id,
        chunk_id=result.chunk_id,
        score=result.score,
        source_id=str(chunk["source_id"]) if chunk.get("source_id") else None,
        normalized_path=str(chunk["normalized_path"]) if chunk.get("normalized_path") else None,
        section=str(chunk["section"]) if chunk.get("section") else None,
        page_number=int(chunk["page_number"]) if chunk.get("page_number") else None,
        image_ids=tuple(str(image_id) for image_id in chunk.get("image_ids", [])),
    )

"""加载检索评测问题，并把原文证据解析到当前文本块。"""

import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class EvidenceReference:
    """表示一处能够独立支持标准答案的原文证据。"""

    source_id: str
    normalized_path: str
    page_number: int | None
    evidence_quote: str


@dataclass(frozen=True)
class RetrievalQuestion:
    """表示一道带标准答案位置的检索评测问题。"""

    question_id: str
    question: str
    expected_answer: str
    source_id: str
    normalized_path: str
    expected_section: str | None
    page_number: int | None
    evidence_quote: str
    category: str
    difficulty: str
    acceptable_evidence: tuple[EvidenceReference, ...]


@dataclass(frozen=True)
class ResolvedQuestion:
    """保存一道问题在当前切分版本中对应的相关文本块编号。"""

    question_id: str
    canonical_chunk_ids: tuple[str, ...]
    relevant_chunk_ids: tuple[str, ...]


def load_retrieval_questions(dataset_path: Path) -> list[RetrievalQuestion]:
    """读取 JSONL 评测集，并检查字段、难度和问题编号。"""
    questions: list[RetrievalQuestion] = []
    seen_ids: set[str] = set()
    with dataset_path.open(encoding="utf-8") as dataset_file:
        for line_number, line in enumerate(dataset_file, start=1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"评测集第 {line_number} 行不是合法 JSON：{error.msg}") from error
            question = _parse_question(payload, line_number)
            if question.question_id in seen_ids:
                raise ValueError(f"评测问题编号重复：{question.question_id}")
            seen_ids.add(question.question_id)
            questions.append(question)
    if not questions:
        raise ValueError(f"评测集不能为空：{dataset_path}")
    return questions


def resolve_relevant_chunks(
    questions: list[RetrievalQuestion],
    chunks_path: Path,
) -> list[ResolvedQuestion]:
    """分别定位指定原文块，以及所有能够支持答案的可接受文本块。"""
    chunks = _load_chunks(chunks_path)
    resolved: list[ResolvedQuestion] = []
    for question in questions:
        canonical = EvidenceReference(
            source_id=question.source_id,
            normalized_path=question.normalized_path,
            page_number=question.page_number,
            evidence_quote=question.evidence_quote,
        )
        canonical_ids = _resolve_evidence(canonical, chunks)
        relevant_ids = list(canonical_ids)
        for evidence in question.acceptable_evidence:
            relevant_ids.extend(_resolve_evidence(evidence, chunks))
        resolved.append(
            ResolvedQuestion(
                question_id=question.question_id,
                canonical_chunk_ids=canonical_ids,
                relevant_chunk_ids=tuple(dict.fromkeys(relevant_ids)),
            )
        )
    return resolved


def validate_retrieval_dataset(
    dataset_path: Path,
    chunks_path: Path,
    output_path: Path | None = None,
) -> dict[str, Any]:
    """校验全部问题都能定位证据，并可选写出当前切分版本的标准块编号。"""
    questions = load_retrieval_questions(dataset_path)
    resolved = resolve_relevant_chunks(questions, chunks_path)
    unresolved_ids = [item.question_id for item in resolved if not item.relevant_chunk_ids]
    canonical_unresolved_ids = [item.question_id for item in resolved if not item.canonical_chunk_ids]
    multiple_match_ids = [item.question_id for item in resolved if len(item.relevant_chunk_ids) > 1]
    source_counts = Counter(question.source_id for question in questions)
    category_counts = Counter(question.category for question in questions)
    report = {
        "question_count": len(questions),
        "resolved_question_count": len(questions) - len(unresolved_ids),
        "unresolved_question_ids": unresolved_ids,
        "canonical_unresolved_question_ids": canonical_unresolved_ids,
        "multiple_match_question_ids": multiple_match_ids,
        "source_question_counts": dict(sorted(source_counts.items())),
        "category_question_counts": dict(sorted(category_counts.items())),
        "questions": [asdict(item) for item in resolved],
    }
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def _parse_question(payload: Any, line_number: int) -> RetrievalQuestion:
    """把单行 JSON 转为强约束数据对象。"""
    if not isinstance(payload, dict):
        raise ValueError(f"评测集第 {line_number} 行必须是 JSON 对象")
    required_string_fields = (
        "question_id",
        "question",
        "expected_answer",
        "source_id",
        "normalized_path",
        "evidence_quote",
        "category",
        "difficulty",
    )
    for field_name in required_string_fields:
        if not isinstance(payload.get(field_name), str) or not payload[field_name].strip():
            raise ValueError(f"评测集第 {line_number} 行缺少字符串字段：{field_name}")
    if payload["difficulty"] not in {"easy", "medium", "hard"}:
        raise ValueError(f"评测集第 {line_number} 行 difficulty 只能是 easy、medium 或 hard")
    expected_section = payload.get("expected_section")
    if expected_section is not None and not isinstance(expected_section, str):
        raise ValueError(f"评测集第 {line_number} 行 expected_section 必须是字符串或 null")
    page_number = payload.get("page_number")
    if page_number is not None and (not isinstance(page_number, int) or page_number <= 0):
        raise ValueError(f"评测集第 {line_number} 行 page_number 必须是正整数或 null")
    acceptable_payload = payload.get("acceptable_evidence", [])
    if not isinstance(acceptable_payload, list):
        raise ValueError(f"评测集第 {line_number} 行 acceptable_evidence 必须是数组")
    acceptable_evidence = tuple(
        _parse_evidence_reference(item, line_number, index)
        for index, item in enumerate(acceptable_payload, start=1)
    )
    return RetrievalQuestion(
        question_id=payload["question_id"],
        question=payload["question"],
        expected_answer=payload["expected_answer"],
        source_id=payload["source_id"],
        normalized_path=payload["normalized_path"],
        expected_section=expected_section,
        page_number=page_number,
        evidence_quote=payload["evidence_quote"],
        category=payload["category"],
        difficulty=payload["difficulty"],
        acceptable_evidence=acceptable_evidence,
    )


def _parse_evidence_reference(payload: Any, line_number: int, evidence_index: int) -> EvidenceReference:
    """校验一条额外可接受证据，防止宽松标注变成无约束匹配。"""
    if not isinstance(payload, dict):
        raise ValueError(f"评测集第 {line_number} 行第 {evidence_index} 条可接受证据必须是对象")
    for field_name in ("source_id", "normalized_path", "evidence_quote"):
        if not isinstance(payload.get(field_name), str) or not payload[field_name].strip():
            raise ValueError(f"评测集第 {line_number} 行可接受证据缺少字符串字段：{field_name}")
    page_number = payload.get("page_number")
    if page_number is not None and (not isinstance(page_number, int) or page_number <= 0):
        raise ValueError(f"评测集第 {line_number} 行可接受证据 page_number 必须是正整数或 null")
    return EvidenceReference(
        source_id=payload["source_id"],
        normalized_path=payload["normalized_path"],
        page_number=page_number,
        evidence_quote=payload["evidence_quote"],
    )


def _resolve_evidence(evidence: EvidenceReference, chunks: list[dict[str, Any]]) -> tuple[str, ...]:
    """使用文件位置和原文片段，将一处证据映射到当前切分版本。"""
    normalized_quote = _normalize_for_match(evidence.evidence_quote)
    matched_ids: list[str] = []
    for chunk in chunks:
        if chunk.get("source_id") != evidence.source_id:
            continue
        if chunk.get("normalized_path") != evidence.normalized_path:
            continue
        if evidence.page_number is not None and chunk.get("page_number") != evidence.page_number:
            continue
        if normalized_quote in _normalize_for_match(str(chunk.get("content", ""))):
            matched_ids.append(str(chunk["chunk_id"]))
    return tuple(dict.fromkeys(matched_ids))


def _load_chunks(chunks_path: Path) -> list[dict[str, Any]]:
    """读取当前切分结果，并拒绝缺少文本块编号的记录。"""
    chunks: list[dict[str, Any]] = []
    with chunks_path.open(encoding="utf-8") as chunks_file:
        for line_number, line in enumerate(chunks_file, start=1):
            if not line.strip():
                continue
            try:
                chunk = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"文本块文件第 {line_number} 行不是合法 JSON：{error.msg}") from error
            if not isinstance(chunk, dict) or not chunk.get("chunk_id"):
                raise ValueError(f"文本块文件第 {line_number} 行缺少 chunk_id")
            chunks.append(chunk)
    return chunks


def _normalize_for_match(text: str) -> str:
    """统一空白字符，使换行不影响短原文证据匹配。"""
    return re.sub(r"\s+", " ", text.replace("\u00a0", " ")).strip()

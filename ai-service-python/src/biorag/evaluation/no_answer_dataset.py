"""加载无答案问题，并校验开发集与独立测试集没有信息泄漏。"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from biorag.evaluation.retrieval_dataset import load_retrieval_questions, resolve_relevant_chunks


@dataclass(frozen=True)
class NoAnswerQuestion:
    """表示知识库中不应存在可靠答案的一道问题。"""

    question_id: str
    question: str
    expected_behavior: str
    category: str
    difficulty: str
    confusing_source_id: str | None


def load_no_answer_questions(dataset_path: Path) -> list[NoAnswerQuestion]:
    """读取无答案 JSONL，并检查必填字段、难度和编号唯一性。"""
    questions: list[NoAnswerQuestion] = []
    seen_ids: set[str] = set()
    with dataset_path.open(encoding="utf-8") as dataset_file:
        for line_number, line in enumerate(dataset_file, start=1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"无答案集第 {line_number} 行不是合法 JSON：{error.msg}") from error
            question = _parse_no_answer_question(payload, line_number)
            if question.question_id in seen_ids:
                raise ValueError(f"无答案问题编号重复：{question.question_id}")
            seen_ids.add(question.question_id)
            questions.append(question)
    if not questions:
        raise ValueError(f"无答案集不能为空：{dataset_path}")
    return questions


def validate_evaluation_isolation(
    development_path: Path,
    test_path: Path,
    chunks_path: Path,
    no_answer_development_path: Path | None = None,
    no_answer_test_path: Path | None = None,
) -> dict[str, Any]:
    """检查开发集与测试集的问题、编号和标准证据块是否完全隔离。"""
    development = load_retrieval_questions(development_path)
    test = load_retrieval_questions(test_path)
    development_resolved = resolve_relevant_chunks(development, chunks_path)
    test_resolved = resolve_relevant_chunks(test, chunks_path)

    development_ids = {question.question_id for question in development}
    test_ids = {question.question_id for question in test}
    development_texts = {_normalize_question(question.question) for question in development}
    test_texts = {_normalize_question(question.question) for question in test}
    development_chunks = {
        chunk_id for item in development_resolved for chunk_id in item.relevant_chunk_ids
    }
    test_chunks = {chunk_id for item in test_resolved for chunk_id in item.relevant_chunk_ids}
    unresolved_test = [item.question_id for item in test_resolved if not item.relevant_chunk_ids]

    report: dict[str, Any] = {
        "development_question_count": len(development),
        "test_question_count": len(test),
        "duplicate_question_ids": sorted(development_ids & test_ids),
        "duplicate_question_texts": sorted(development_texts & test_texts),
        "shared_relevant_chunk_ids": sorted(development_chunks & test_chunks),
        "unresolved_test_question_ids": unresolved_test,
    }
    if no_answer_development_path is not None and no_answer_test_path is not None:
        no_answer_development = load_no_answer_questions(no_answer_development_path)
        no_answer_test = load_no_answer_questions(no_answer_test_path)
        dev_no_answer_texts = {
            _normalize_question(question.question) for question in no_answer_development
        }
        test_no_answer_texts = {_normalize_question(question.question) for question in no_answer_test}
        report.update(
            {
                "no_answer_development_count": len(no_answer_development),
                "no_answer_test_count": len(no_answer_test),
                "duplicate_no_answer_texts": sorted(dev_no_answer_texts & test_no_answer_texts),
            }
        )
    report["isolated"] = not any(
        report[key]
        for key in (
            "duplicate_question_ids",
            "duplicate_question_texts",
            "shared_relevant_chunk_ids",
            "unresolved_test_question_ids",
            "duplicate_no_answer_texts",
        )
        if key in report
    )
    return report


def _parse_no_answer_question(payload: Any, line_number: int) -> NoAnswerQuestion:
    """把单行 JSON 转换为强约束无答案问题对象。"""
    if not isinstance(payload, dict):
        raise ValueError(f"无答案集第 {line_number} 行必须是 JSON 对象")
    required_fields = ("question_id", "question", "expected_behavior", "category", "difficulty")
    for field_name in required_fields:
        if not isinstance(payload.get(field_name), str) or not payload[field_name].strip():
            raise ValueError(f"无答案集第 {line_number} 行缺少字符串字段：{field_name}")
    if payload["difficulty"] not in {"easy", "medium", "hard"}:
        raise ValueError(f"无答案集第 {line_number} 行 difficulty 不合法")
    confusing_source_id = payload.get("confusing_source_id")
    if confusing_source_id is not None and not isinstance(confusing_source_id, str):
        raise ValueError(f"无答案集第 {line_number} 行 confusing_source_id 必须是字符串或 null")
    return NoAnswerQuestion(
        question_id=payload["question_id"],
        question=payload["question"],
        expected_behavior=payload["expected_behavior"],
        category=payload["category"],
        difficulty=payload["difficulty"],
        confusing_source_id=confusing_source_id,
    )


def _normalize_question(question: str) -> str:
    """统一问题空白和大小写，用于识别直接重复。"""
    return " ".join(question.casefold().split())

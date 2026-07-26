"""评测集隔离规则测试。"""

import json
from pathlib import Path

from biorag.evaluation.no_answer_dataset import load_no_answer_questions, validate_evaluation_isolation


def _write_jsonl(path: Path, records: list[dict[str, object]]) -> None:
    """写入临时 JSONL 测试文件。"""
    path.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )


def _answerable(question_id: str, question: str, chunk_id: str) -> dict[str, object]:
    """创建最小可定位的有答案问题。"""
    return {
        "question_id": question_id,
        "question": question,
        "expected_answer": "答案",
        "source_id": "guide",
        "normalized_path": "guide.md",
        "expected_section": "section",
        "page_number": None,
        "evidence_quote": chunk_id,
        "category": "test",
        "difficulty": "easy",
    }


def test_isolation_rejects_shared_relevant_chunks(tmp_path: Path) -> None:
    """开发集和测试集复用同一标准块时必须判定为未隔离。"""
    development = tmp_path / "development.jsonl"
    test = tmp_path / "test.jsonl"
    chunks = tmp_path / "chunks.jsonl"
    _write_jsonl(development, [_answerable("dev-001", "开发问题", "shared evidence")])
    _write_jsonl(test, [_answerable("test-001", "测试问题", "shared evidence")])
    _write_jsonl(
        chunks,
        [{"chunk_id": "chunk-001", "source_id": "guide", "normalized_path": "guide.md", "content": "shared evidence"}],
    )

    report = validate_evaluation_isolation(development, test, chunks)

    assert report["shared_relevant_chunk_ids"] == ["chunk-001"]
    assert report["isolated"] is False


def test_no_answer_loader_reads_expected_refusal(tmp_path: Path) -> None:
    """无答案问题使用独立数据结构，不要求原文证据字段。"""
    path = tmp_path / "no-answer.jsonl"
    _write_jsonl(
        path,
        [
            {
                "question_id": "no-001",
                "question": "知识库没有这个工具吗？",
                "expected_behavior": "拒答",
                "category": "缺失工具",
                "difficulty": "easy",
                "confusing_source_id": None,
            }
        ],
    )

    questions = load_no_answer_questions(path)

    assert questions[0].expected_behavior == "拒答"

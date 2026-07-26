"""检索评测集加载和证据定位测试。"""

import json
from pathlib import Path

import pytest

from biorag.evaluation.retrieval_dataset import load_retrieval_questions, validate_retrieval_dataset


def _write_jsonl(path: Path, records: list[dict[str, object]]) -> None:
    """把测试记录写成逐行 JSON 文件。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )


def _question(question_id: str = "q-001") -> dict[str, object]:
    """创建一条字段完整的测试问题。"""
    return {
        "question_id": question_id,
        "question": "为什么需要原始计数？",
        "expected_answer": "模型需要原始计数评估测量精度。",
        "source_id": "guide",
        "normalized_path": "guide/guide.md",
        "expected_section": "Input data",
        "page_number": None,
        "evidence_quote": "only the count values allow assessing the measurement precision correctly",
        "category": "差异分析",
        "difficulty": "medium",
    }


def test_validation_resolves_evidence_across_line_breaks(tmp_path: Path) -> None:
    """原文中的换行不能阻止问题解析到相关文本块。"""
    dataset_path = tmp_path / "questions.jsonl"
    chunks_path = tmp_path / "chunks.jsonl"
    output_path = tmp_path / "ground-truth.json"
    _write_jsonl(dataset_path, [_question()])
    _write_jsonl(
        chunks_path,
        [
            {
                "chunk_id": "chunk-001",
                "source_id": "guide",
                "normalized_path": "guide/guide.md",
                "page_number": None,
                "content": "only the count values allow assessing\nthe measurement precision correctly",
            }
        ],
    )

    report = validate_retrieval_dataset(dataset_path, chunks_path, output_path)

    assert report["resolved_question_count"] == 1
    assert report["questions"][0]["relevant_chunk_ids"] == ("chunk-001",)
    assert output_path.exists()


def test_validation_resolves_multiple_acceptable_evidence_locations(tmp_path: Path) -> None:
    """同一答案位于教程和参考手册时，两处文本块都应被视为正确。"""
    dataset_path = tmp_path / "questions.jsonl"
    chunks_path = tmp_path / "chunks.jsonl"
    question = _question()
    question["acceptable_evidence"] = [
        {
            "source_id": "guide",
            "normalized_path": "guide/tutorial.md",
            "page_number": None,
            "evidence_quote": "模型可以从原始计数判断测量精度",
        }
    ]
    _write_jsonl(dataset_path, [question])
    _write_jsonl(
        chunks_path,
        [
            {
                "chunk_id": "canonical",
                "source_id": "guide",
                "normalized_path": "guide/guide.md",
                "content": "only the count values allow assessing the measurement precision correctly",
            },
            {
                "chunk_id": "tutorial",
                "source_id": "guide",
                "normalized_path": "guide/tutorial.md",
                "content": "模型可以从原始计数判断测量精度。",
            },
        ],
    )

    report = validate_retrieval_dataset(dataset_path, chunks_path)

    resolved = report["questions"][0]
    assert resolved["canonical_chunk_ids"] == ("canonical",)
    assert resolved["relevant_chunk_ids"] == ("canonical", "tutorial")


def test_loader_rejects_duplicate_question_ids(tmp_path: Path) -> None:
    """重复问题编号会破坏指标统计，必须在加载时拒绝。"""
    dataset_path = tmp_path / "questions.jsonl"
    _write_jsonl(dataset_path, [_question(), _question()])

    with pytest.raises(ValueError, match="编号重复"):
        load_retrieval_questions(dataset_path)

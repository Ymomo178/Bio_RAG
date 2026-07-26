"""本地稠密向量索引和评测指标测试。"""

import json
from pathlib import Path

import numpy as np

from biorag.evaluation.dense_evaluator import evaluate_dense_retrieval
from biorag.retrieval.dense import DenseIndex, build_dense_index


class FakeEmbedder:
    """使用固定词语规则产生二维向量，避免单元测试下载真实模型。"""

    model_name = "fake-embedder"
    max_sequence_length = 10

    def encode_queries(self, texts: list[str]) -> np.ndarray:
        """把含苹果的问题映射到第一维，其余映射到第二维。"""
        return self._encode(texts)

    def encode_passages(self, texts: list[str]) -> np.ndarray:
        """使用与问题相同的规则编码文本块。"""
        return self._encode(texts)

    def count_tokens(self, texts: list[str]) -> list[int]:
        """以空格分隔数量模拟 Token 长度。"""
        return [len(text.split()) for text in texts]

    def _encode(self, texts: list[str]) -> np.ndarray:
        """返回已经归一化的测试向量。"""
        return np.asarray([[1.0, 0.0] if "苹果" in text else [0.0, 1.0] for text in texts], dtype=np.float32)


def _write_jsonl(path: Path, records: list[dict[str, object]]) -> None:
    """写入测试使用的逐行 JSON。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )


def test_dense_index_build_search_and_evaluate(tmp_path: Path) -> None:
    """正确文本块应排在第一名，并产生满分 Hit 和 MRR。"""
    chunks_path = tmp_path / "chunks.jsonl"
    dataset_path = tmp_path / "questions.jsonl"
    index_directory = tmp_path / "index"
    _write_jsonl(
        chunks_path,
        [
            {
                "chunk_id": "fruit",
                "source_id": "guide",
                "normalized_path": "guide.md",
                "embedding_text": "苹果 是 水果",
                "content": "苹果是水果。",
            },
            {
                "chunk_id": "tool",
                "source_id": "other",
                "normalized_path": "other.md",
                "embedding_text": "扳手 是 工具",
                "content": "扳手是工具。",
            },
        ],
    )
    _write_jsonl(
        dataset_path,
        [
            {
                "question_id": "q-001",
                "question": "苹果是什么？",
                "expected_answer": "水果。",
                "source_id": "guide",
                "normalized_path": "guide.md",
                "expected_section": None,
                "page_number": None,
                "evidence_quote": "苹果是水果",
                "category": "测试",
                "difficulty": "easy",
            }
        ],
    )
    embedder = FakeEmbedder()

    index, manifest = build_dense_index(chunks_path, index_directory, embedder)
    report = evaluate_dense_retrieval(dataset_path, chunks_path, index, embedder)

    assert index.search(np.asarray([1.0, 0.0], dtype=np.float32), 1)[0].chunk_id == "fruit"
    assert manifest["embedding_dimension"] == 2
    assert report["metrics"]["hit_at_1"] == 1.0
    assert report["metrics"]["mrr_at_10"] == 1.0


def test_evaluation_separates_answerable_and_canonical_metrics(tmp_path: Path) -> None:
    """命中等价教程证据时应算可回答，但不能伪装成指定原文命中。"""
    chunks_path = tmp_path / "chunks.jsonl"
    dataset_path = tmp_path / "questions.jsonl"
    index_directory = tmp_path / "index"
    _write_jsonl(
        chunks_path,
        [
            {
                "chunk_id": "canonical",
                "source_id": "guide",
                "normalized_path": "guide/reference.md",
                "embedding_text": "香蕉 是 水果",
                "content": "香蕉是水果。",
            },
            {
                "chunk_id": "tutorial",
                "source_id": "guide",
                "normalized_path": "guide/tutorial.md",
                "embedding_text": "苹果 是 水果",
                "content": "苹果是水果。",
            },
        ],
    )
    _write_jsonl(
        dataset_path,
        [
            {
                "question_id": "q-001",
                "question": "苹果是什么？",
                "expected_answer": "水果。",
                "source_id": "guide",
                "normalized_path": "guide/reference.md",
                "expected_section": None,
                "page_number": None,
                "evidence_quote": "香蕉是水果",
                "category": "测试",
                "difficulty": "easy",
                "acceptable_evidence": [
                    {
                        "source_id": "guide",
                        "normalized_path": "guide/tutorial.md",
                        "page_number": None,
                        "evidence_quote": "苹果是水果",
                    }
                ],
            }
        ],
    )
    embedder = FakeEmbedder()

    index, _ = build_dense_index(chunks_path, index_directory, embedder)
    report = evaluate_dense_retrieval(
        dataset_path,
        chunks_path,
        index,
        embedder,
        top_ks=(1, 2),
    )

    assert report["metrics"]["hit_at_1"] == 1.0
    assert report["canonical_metrics"]["hit_at_1"] == 0.0
    assert report["canonical_metrics"]["hit_at_2"] == 1.0

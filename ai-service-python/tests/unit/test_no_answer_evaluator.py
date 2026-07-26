"""无答案拒答评测的单元测试。"""

from dataclasses import dataclass
from pathlib import Path

from biorag.evaluation.no_answer_evaluator import evaluate_no_answer_retrieval
from biorag.retrieval.dense import SearchResult


@dataclass
class FakeRetriever:
    """根据问题文本返回固定分数的假检索器。"""

    def search(self, query: str, top_k: int) -> list[SearchResult]:
        """模拟最高证据分数。"""
        score = 0.9 if "拒答" in query else 0.2
        return [SearchResult("chunk-1", score, {"content": "test"})]


def test_no_answer_report_counts_false_accepts(tmp_path: Path) -> None:
    """达到阈值的无答案问题应计为误接受。"""
    dataset = tmp_path / "no-answer.jsonl"
    dataset.write_text(
        '{"question_id":"no-1","question":"请拒答","expected_behavior":"拒答","category":"test","difficulty":"easy"}\n'
        '{"question_id":"no-2","question":"没有证据","expected_behavior":"拒答","category":"test","difficulty":"easy"}\n',
        encoding="utf-8",
    )

    report = evaluate_no_answer_retrieval(dataset, FakeRetriever(), 0.85)

    assert report["question_count"] == 2
    assert report["false_accept_count"] == 1
    assert report["rejection_count"] == 1

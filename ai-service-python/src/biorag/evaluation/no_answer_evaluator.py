"""评估检索系统对知识库外问题的拒答能力。"""

from pathlib import Path
from typing import Any

from biorag.evaluation.no_answer_dataset import load_no_answer_questions


def evaluate_no_answer_retrieval(
    dataset_path: Path,
    retriever: Any,
    score_threshold: float,
    metadata: dict[str, Any] | None = None,
    output_path: Path | None = None,
    top_k: int = 1,
) -> dict[str, Any]:
    """用开发集校准后的分数阈值统计无答案问题的误接受率。"""
    if not 0 <= score_threshold <= 1:
        raise ValueError("score_threshold 必须在 0 和 1 之间")
    if top_k <= 0:
        raise ValueError("top_k 必须大于 0")

    questions = load_no_answer_questions(dataset_path)
    details: list[dict[str, Any]] = []
    for question in questions:
        results = retriever.search(question.question, top_k)
        top_result = results[0] if results else None
        top_score = float(top_result.score) if top_result is not None else None
        accepted_as_evidence = top_score is not None and top_score >= score_threshold
        details.append(
            {
                "question_id": question.question_id,
                "question": question.question,
                "category": question.category,
                "difficulty": question.difficulty,
                "confusing_source_id": question.confusing_source_id,
                "top_score": top_score,
                "accepted_as_evidence": accepted_as_evidence,
                "top_chunk_id": top_result.chunk_id if top_result is not None else None,
            }
        )

    false_accept_count = sum(item["accepted_as_evidence"] for item in details)
    total = len(details)
    report: dict[str, Any] = {
        "evaluation_type": "no_answer_rejection",
        "dataset": str(dataset_path),
        "question_count": total,
        "score_threshold": score_threshold,
        "top_k": top_k,
        "false_accept_count": false_accept_count,
        "false_accept_rate": round(false_accept_count / total, 4) if total else 0.0,
        "rejection_count": total - false_accept_count,
        "rejection_rate": round((total - false_accept_count) / total, 4) if total else 0.0,
        "metadata": metadata or {},
        "details": details,
    }
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        import json

        output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report

"""使用统一评测标准验证混合检索和重排序效果。"""

from pathlib import Path
from typing import Any

from biorag.evaluation.retrieval_dataset import load_retrieval_questions, resolve_relevant_chunks
from biorag.evaluation.retrieval_metrics import build_retrieval_report
from biorag.retrieval.hybrid import HybridRetriever


def evaluate_hybrid_retrieval(
    dataset_path: Path,
    chunks_path: Path,
    retriever: HybridRetriever,
    metadata: dict[str, Any],
    output_path: Path | None = None,
    top_ks: tuple[int, ...] = (1, 3, 5, 10),
) -> dict[str, Any]:
    """逐题执行混合检索，并生成与稠密基线可直接比较的报告。"""
    questions = load_retrieval_questions(dataset_path)
    resolved = resolve_relevant_chunks(questions, chunks_path)
    maximum_k = max(top_ks)
    results_by_question = {
        question.question_id: retriever.search(question.question, maximum_k)
        for question in questions
    }
    return build_retrieval_report(
        questions=questions,
        resolved=resolved,
        results_by_question=results_by_question,
        metadata=metadata,
        output_path=output_path,
        top_ks=top_ks,
    )

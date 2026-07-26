"""统一计算稠密检索、混合检索和重排序检索的评测指标。"""

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from biorag.evaluation.retrieval_dataset import ResolvedQuestion, RetrievalQuestion
from biorag.retrieval.dense import SearchResult


def build_retrieval_report(
    questions: list[RetrievalQuestion],
    resolved: list[ResolvedQuestion],
    results_by_question: dict[str, list[SearchResult]],
    metadata: dict[str, Any],
    output_path: Path | None = None,
    top_ks: tuple[int, ...] = (1, 3, 5, 10),
) -> dict[str, Any]:
    """根据统一的标准证据计算 Hit@K、MRR 和分来源指标。"""
    if not top_ks or any(value <= 0 for value in top_ks):
        raise ValueError("top_ks 必须全部为正整数")
    relevant_by_id = {item.question_id: set(item.relevant_chunk_ids) for item in resolved}
    canonical_by_id = {item.question_id: set(item.canonical_chunk_ids) for item in resolved}
    unresolved = [question.question_id for question in questions if not relevant_by_id.get(question.question_id)]
    if unresolved:
        raise ValueError(f"以下评测问题没有标准文本块：{', '.join(unresolved)}")

    hit_counts = {top_k: 0 for top_k in top_ks}
    canonical_hit_counts = {top_k: 0 for top_k in top_ks}
    reciprocal_ranks: list[float] = []
    canonical_reciprocal_ranks: list[float] = []
    source_hits: dict[str, list[bool]] = defaultdict(list)
    canonical_source_hits: dict[str, list[bool]] = defaultdict(list)
    details: list[dict[str, Any]] = []
    maximum_k = max(top_ks)

    for question in questions:
        relevant_ids = relevant_by_id[question.question_id]
        canonical_ids = canonical_by_id[question.question_id]
        results = results_by_question.get(question.question_id, [])[:maximum_k]
        result_ids = [result.chunk_id for result in results]
        first_rank = _first_relevant_rank(result_ids, relevant_ids)
        first_canonical_rank = _first_relevant_rank(result_ids, canonical_ids)

        for top_k in top_ks:
            hit_counts[top_k] += int(any(chunk_id in relevant_ids for chunk_id in result_ids[:top_k]))
            canonical_hit_counts[top_k] += int(
                any(chunk_id in canonical_ids for chunk_id in result_ids[:top_k])
            )
        source_hits[question.source_id].append(
            any(chunk_id in relevant_ids for chunk_id in result_ids[:5])
        )
        canonical_source_hits[question.source_id].append(
            any(chunk_id in canonical_ids for chunk_id in result_ids[:5])
        )
        reciprocal_ranks.append(1.0 / first_rank if first_rank is not None else 0.0)
        canonical_reciprocal_ranks.append(
            1.0 / first_canonical_rank if first_canonical_rank is not None else 0.0
        )
        details.append(
            {
                "question_id": question.question_id,
                "question": question.question,
                "source_id": question.source_id,
                "first_relevant_rank": first_rank,
                "first_canonical_rank": first_canonical_rank,
                "canonical_chunk_ids": sorted(canonical_ids),
                "relevant_chunk_ids": sorted(relevant_ids),
                "results": [_serialize_result(result, rank) for rank, result in enumerate(results, start=1)],
            }
        )

    question_count = len(questions)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        **metadata,
        "question_count": question_count,
        "evaluation_standard": {
            "metrics": "命中任一经过人工核验、能够独立支持答案的证据块",
            "canonical_metrics": "仅命中每题最初指定的官方原文块，用于保持历史对比",
        },
        "metrics": _metrics(hit_counts, reciprocal_ranks, question_count, maximum_k),
        "canonical_metrics": _metrics(
            canonical_hit_counts,
            canonical_reciprocal_ranks,
            question_count,
            maximum_k,
        ),
        "source_hit_at_5": _source_metrics(source_hits),
        "canonical_source_hit_at_5": _source_metrics(canonical_source_hits),
        "details": details,
    }
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def _first_relevant_rank(result_ids: list[str], relevant_ids: set[str]) -> int | None:
    """返回第一个正确文本块的排名，没有命中时返回空值。"""
    return next(
        (rank for rank, chunk_id in enumerate(result_ids, start=1) if chunk_id in relevant_ids),
        None,
    )


def _metrics(
    hit_counts: dict[int, int],
    reciprocal_ranks: list[float],
    question_count: int,
    maximum_k: int,
) -> dict[str, float]:
    """把命中数量和倒数排名转换为标准化指标。"""
    return {
        **{f"hit_at_{top_k}": round(count / question_count, 4) for top_k, count in hit_counts.items()},
        f"mrr_at_{maximum_k}": round(float(np.mean(reciprocal_ranks)), 4),
    }


def _source_metrics(source_hits: dict[str, list[bool]]) -> dict[str, float]:
    """计算每个文档来源的 Hit@5。"""
    return {
        source_id: round(sum(hits) / len(hits), 4)
        for source_id, hits in sorted(source_hits.items())
    }


def _serialize_result(result: SearchResult, rank: int) -> dict[str, Any]:
    """保存检索结果的排名、分数和可追踪来源信息。"""
    return {
        "rank": rank,
        "chunk_id": result.chunk_id,
        "score": round(result.score, 6),
        "source_id": result.chunk.get("source_id"),
        "normalized_path": result.chunk.get("normalized_path"),
        "section": result.chunk.get("section"),
        "page_number": result.chunk.get("page_number"),
    }

"""使用带标准证据的问题评测稠密向量检索。"""

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from biorag.evaluation.retrieval_dataset import load_retrieval_questions, resolve_relevant_chunks
from biorag.retrieval.dense import DenseIndex, TextEmbedder


def evaluate_dense_retrieval(
    dataset_path: Path,
    chunks_path: Path,
    index: DenseIndex,
    embedder: TextEmbedder,
    output_path: Path | None = None,
    top_ks: tuple[int, ...] = (1, 3, 5, 10),
) -> dict[str, Any]:
    """运行全部问题，计算 Hit@K、MRR 和按来源拆分的 Hit@5。"""
    questions = load_retrieval_questions(dataset_path)
    resolved = resolve_relevant_chunks(questions, chunks_path)
    relevant_by_id = {item.question_id: set(item.relevant_chunk_ids) for item in resolved}
    canonical_by_id = {item.question_id: set(item.canonical_chunk_ids) for item in resolved}
    unresolved = [question_id for question_id, ids in relevant_by_id.items() if not ids]
    if unresolved:
        raise ValueError(f"以下评测问题没有标准文本块：{', '.join(unresolved)}")
    if not top_ks or any(value <= 0 for value in top_ks):
        raise ValueError("top_ks 必须全部为正整数")

    query_vectors = embedder.encode_queries([question.question for question in questions])
    maximum_k = max(top_ks)
    hit_counts = {top_k: 0 for top_k in top_ks}
    canonical_hit_counts = {top_k: 0 for top_k in top_ks}
    reciprocal_ranks: list[float] = []
    canonical_reciprocal_ranks: list[float] = []
    source_hits: dict[str, list[bool]] = defaultdict(list)
    canonical_source_hits: dict[str, list[bool]] = defaultdict(list)
    details: list[dict[str, Any]] = []

    for question, query_vector in zip(questions, query_vectors, strict=True):
        relevant_ids = relevant_by_id[question.question_id]
        canonical_ids = canonical_by_id[question.question_id]
        results = index.search(query_vector, maximum_k)
        result_ids = [result.chunk_id for result in results]
        first_rank = next(
            (rank for rank, chunk_id in enumerate(result_ids, start=1) if chunk_id in relevant_ids),
            None,
        )
        first_canonical_rank = next(
            (rank for rank, chunk_id in enumerate(result_ids, start=1) if chunk_id in canonical_ids),
            None,
        )
        for top_k in top_ks:
            if any(chunk_id in relevant_ids for chunk_id in result_ids[:top_k]):
                hit_counts[top_k] += 1
            if any(chunk_id in canonical_ids for chunk_id in result_ids[:top_k]):
                canonical_hit_counts[top_k] += 1
        hit_at_five = any(chunk_id in relevant_ids for chunk_id in result_ids[:5])
        canonical_hit_at_five = any(chunk_id in canonical_ids for chunk_id in result_ids[:5])
        source_hits[question.source_id].append(hit_at_five)
        canonical_source_hits[question.source_id].append(canonical_hit_at_five)
        reciprocal_ranks.append(1.0 / first_rank if first_rank is not None else 0.0)
        canonical_reciprocal_ranks.append(1.0 / first_canonical_rank if first_canonical_rank is not None else 0.0)
        details.append(
            {
                "question_id": question.question_id,
                "question": question.question,
                "source_id": question.source_id,
                "first_relevant_rank": first_rank,
                "first_canonical_rank": first_canonical_rank,
                "canonical_chunk_ids": sorted(canonical_ids),
                "relevant_chunk_ids": sorted(relevant_ids),
                "results": [
                    {
                        "rank": rank,
                        "chunk_id": result.chunk_id,
                        "score": round(result.score, 6),
                        "source_id": result.chunk.get("source_id"),
                        "section": result.chunk.get("section"),
                        "page_number": result.chunk.get("page_number"),
                    }
                    for rank, result in enumerate(results, start=1)
                ],
            }
        )

    question_count = len(questions)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model_name": embedder.model_name,
        "device": str(getattr(embedder, "device", "unknown")),
        "precision": str(getattr(embedder, "precision", "unknown")),
        "question_count": question_count,
        "evaluation_standard": {
            "metrics": "命中任一经过人工核验、能够独立支持答案的证据块",
            "canonical_metrics": "仅命中每题最初指定的官方原文块，用于保持历史对比",
        },
        "metrics": {
            **{f"hit_at_{top_k}": round(hit_counts[top_k] / question_count, 4) for top_k in top_ks},
            f"mrr_at_{maximum_k}": round(float(np.mean(reciprocal_ranks)), 4),
        },
        "canonical_metrics": {
            **{
                f"hit_at_{top_k}": round(canonical_hit_counts[top_k] / question_count, 4)
                for top_k in top_ks
            },
            f"mrr_at_{maximum_k}": round(float(np.mean(canonical_reciprocal_ranks)), 4),
        },
        "source_hit_at_5": {
            source_id: round(sum(hits) / len(hits), 4)
            for source_id, hits in sorted(source_hits.items())
        },
        "canonical_source_hit_at_5": {
            source_id: round(sum(hits) / len(hits), 4)
            for source_id, hits in sorted(canonical_source_hits.items())
        },
        "details": details,
    }
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report

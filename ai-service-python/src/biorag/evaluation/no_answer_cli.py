"""运行无答案问题拒答评测的命令行入口。"""

import argparse
import os
from pathlib import Path

from biorag.evaluation.no_answer_evaluator import evaluate_no_answer_retrieval
from biorag.retrieval.dense import SentenceTransformerEmbedder, load_or_build_dense_index
from biorag.retrieval.hybrid import (
    BM25KeywordIndex,
    CrossEncoderReranker,
    HybridRetriever,
    HybridSearchConfig,
)


def main() -> None:
    """加载检索组件并输出无答案拒答报告。"""
    parser = argparse.ArgumentParser(description="评测 Bio-RAG 对知识库外问题的拒答能力")
    parser.add_argument("--chunks", type=Path, required=True, help="文本块 JSONL 文件")
    parser.add_argument("--dataset", type=Path, required=True, help="无答案问题 JSONL 文件")
    parser.add_argument("--index", type=Path, required=True, help="本地向量索引目录")
    parser.add_argument("--output", type=Path, required=True, help="评测报告 JSON 文件")
    parser.add_argument("--model", default="BAAI/bge-m3", help="Embedding 模型名称")
    parser.add_argument(
        "--reranker",
        default=os.getenv("RERANKER_MODEL_PATH") or os.getenv("RERANKER_MODEL") or "BAAI/bge-reranker-v2-m3",
        help="Reranker 模型名称或本地目录",
    )
    parser.add_argument("--device", default="cuda", help="模型设备")
    parser.add_argument("--batch-size", type=int, default=4, help="Embedding 批大小")
    parser.add_argument("--reranker-batch-size", type=int, default=4, help="Reranker 批大小")
    parser.add_argument("--dense-candidates", type=int, default=100, help="稠密检索候选数量")
    parser.add_argument("--keyword-candidates", type=int, default=100, help="BM25 候选数量")
    parser.add_argument("--rerank-candidates", type=int, default=100, help="Reranker 候选数量")
    parser.add_argument("--score-threshold", type=float, default=0.85, help="拒答阈值，建议由开发集校准")
    parser.add_argument("--no-reranker", action="store_true", help="不加载 Reranker")
    args = parser.parse_args()

    embedder = SentenceTransformerEmbedder(args.model, args.device, args.batch_size)
    dense_index, manifest, _ = load_or_build_dense_index(args.chunks, args.index, embedder)
    reranker = None if args.no_reranker else CrossEncoderReranker(args.reranker, args.device, args.reranker_batch_size)
    config = HybridSearchConfig(
        dense_candidate_count=args.dense_candidates,
        keyword_candidate_count=args.keyword_candidates,
        rerank_candidate_count=args.rerank_candidates,
    )
    retriever = HybridRetriever(
        dense_index,
        embedder,
        BM25KeywordIndex(dense_index.chunks),
        reranker,
        config,
    )
    report = evaluate_no_answer_retrieval(
        args.dataset,
        retriever,
        args.score_threshold,
        metadata={
            "retrieval_mode": "hybrid_rerank" if reranker is not None else "hybrid",
            "embedding_model": embedder.model_name,
            "embedding_device": embedder.device,
            "embedding_precision": embedder.precision,
            "reranker_model": args.reranker if reranker is not None else None,
            "reranker_device": reranker.device if reranker is not None else None,
            "reranker_precision": reranker.precision if reranker is not None else None,
            "token_statistics": manifest["token_statistics"],
        },
        output_path=args.output,
    )
    print(f"无答案问题数：{report['question_count']}")
    print(f"拒答率：{report['rejection_rate']}")
    print(f"误接受率：{report['false_accept_rate']}")
    print(f"报告文件：{args.output.resolve()}")


if __name__ == "__main__":
    main()

"""运行 BM25、BGE-M3 和可选 Reranker 的完整检索评测。"""

import argparse
import os
from pathlib import Path

from biorag.evaluation.hybrid_evaluator import evaluate_hybrid_retrieval
from biorag.retrieval.dense import SentenceTransformerEmbedder, load_or_build_dense_index
from biorag.retrieval.hybrid import (
    BM25KeywordIndex,
    CrossEncoderReranker,
    HybridRetriever,
    HybridSearchConfig,
)


def main() -> None:
    """解析命令行参数，构建检索组件并输出评测报告。"""
    parser = argparse.ArgumentParser(description="评测 Bio-RAG 混合检索和重排序")
    parser.add_argument("--chunks", type=Path, required=True, help="文本块 JSONL 文件")
    parser.add_argument("--dataset", type=Path, required=True, help="检索评测集 JSONL 文件")
    parser.add_argument("--index", type=Path, required=True, help="BGE-M3 本地向量索引目录")
    parser.add_argument("--output", type=Path, required=True, help="评测报告 JSON 文件")
    parser.add_argument("--model", default="BAAI/bge-m3", help="Embedding 模型名称")
    default_reranker = (
        os.getenv("RERANKER_MODEL_PATH")
        or os.getenv("RERANKER_MODEL")
        or "BAAI/bge-reranker-v2-m3"
    )
    parser.add_argument("--reranker", default=default_reranker, help="Reranker 模型名称或本地目录")
    parser.add_argument(
        "--reranker-name",
        default=os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3"),
        help="写入评测报告的 Reranker 标准名称",
    )
    parser.add_argument("--device", default="cuda", help="模型设备，例如 cuda 或 cpu")
    parser.add_argument("--batch-size", type=int, default=4, help="Embedding 批大小")
    parser.add_argument("--reranker-batch-size", type=int, default=4, help="Reranker 批大小")
    parser.add_argument("--dense-candidates", type=int, default=50, help="稠密检索候选数量")
    parser.add_argument("--keyword-candidates", type=int, default=50, help="BM25 候选数量")
    parser.add_argument("--rerank-candidates", type=int, default=100, help="送入 Reranker 的候选数量")
    parser.add_argument("--no-reranker", action="store_true", help="只评测混合召回，不加载 Reranker")
    args = parser.parse_args()

    embedder = SentenceTransformerEmbedder(args.model, args.device, args.batch_size)
    dense_index, manifest, rebuilt = load_or_build_dense_index(args.chunks, args.index, embedder)
    keyword_index = BM25KeywordIndex(dense_index.chunks)
    reranker = None
    if not args.no_reranker:
        reranker = CrossEncoderReranker(
            model_name=args.reranker,
            device=args.device,
            batch_size=args.reranker_batch_size,
        )
    config = HybridSearchConfig(
        dense_candidate_count=args.dense_candidates,
        keyword_candidate_count=args.keyword_candidates,
        rerank_candidate_count=args.rerank_candidates,
    )
    retriever = HybridRetriever(dense_index, embedder, keyword_index, reranker, config)
    metadata = {
        "retrieval_mode": "hybrid_rerank" if reranker is not None else "hybrid",
        "embedding_model": embedder.model_name,
        "embedding_device": embedder.device,
        "embedding_precision": embedder.precision,
        "keyword_model": "BM25Okapi",
        "fusion": "RRF",
        "reranker_model": args.reranker_name if reranker is not None else None,
        "reranker_source": args.reranker if reranker is not None else None,
        "reranker_device": reranker.device if reranker is not None else None,
        "reranker_precision": reranker.precision if reranker is not None else None,
        "config": {
            "dense_candidate_count": config.dense_candidate_count,
            "keyword_candidate_count": config.keyword_candidate_count,
            "rerank_candidate_count": config.rerank_candidate_count,
            "rrf_k": config.rrf_k,
        },
        "token_statistics": manifest["token_statistics"],
    }
    report = evaluate_hybrid_retrieval(
        args.dataset,
        args.chunks,
        retriever,
        metadata,
        args.output,
    )

    action = "重建" if rebuilt else "复用"
    print(f"向量索引已{action}：{len(dense_index.chunks)} 个文本块")
    print(f"检索模式：{metadata['retrieval_mode']}")
    print(f"检索评测：{report['metrics']}")
    print(f"报告文件：{args.output.resolve()}")


if __name__ == "__main__":
    main()

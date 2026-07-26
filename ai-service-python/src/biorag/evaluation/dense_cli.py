"""本地稠密向量检索评测命令行入口。"""

import argparse
from pathlib import Path

from biorag.evaluation.dense_evaluator import evaluate_dense_retrieval
from biorag.retrieval.dense import SentenceTransformerEmbedder, load_or_build_dense_index


def build_parser() -> argparse.ArgumentParser:
    """创建本地 Embedding 检索评测参数解析器。"""
    parser = argparse.ArgumentParser(description="构建本地向量索引并运行检索评测")
    parser.add_argument("--chunks", type=Path, required=True, help="chunks.jsonl 路径")
    parser.add_argument("--dataset", type=Path, required=True, help="检索问题 JSONL 路径")
    parser.add_argument("--index", type=Path, required=True, help="本地向量索引目录")
    parser.add_argument("--output", type=Path, required=True, help="评测报告 JSON 路径")
    parser.add_argument("--model", default="BAAI/bge-m3", help="Embedding 模型名称")
    parser.add_argument("--device", help="模型设备，例如 cuda 或 cpu；默认自动选择")
    parser.add_argument("--batch-size", type=int, default=8, help="模型批处理大小")
    return parser


def main() -> None:
    """加载模型、构建或复用索引，并输出核心检索指标。"""
    args = build_parser().parse_args()
    embedder = SentenceTransformerEmbedder(args.model, args.device, args.batch_size)
    index, manifest, rebuilt = load_or_build_dense_index(args.chunks, args.index, embedder)
    report = evaluate_dense_retrieval(args.dataset, args.chunks, index, embedder, args.output)
    action = "已重新构建" if rebuilt else "已复用"
    print(f"向量索引{action}：{manifest['chunk_count']} 个文本块，模型 {args.model}")
    print(f"Token 统计：{manifest['token_statistics']}")
    print(f"检索评测：{report['metrics']}")
    print(f"报告文件：{args.output.resolve()}")


if __name__ == "__main__":
    main()

"""文本切分命令行入口。"""

import argparse
from pathlib import Path

from biorag.ingestion.chunking import ChunkingConfig, chunk_normalized_directory


def build_parser() -> argparse.ArgumentParser:
    """创建文本切分命令的参数解析器。"""
    parser = argparse.ArgumentParser(description="把规范化 Markdown 切分为 RAG 文本块")
    parser.add_argument("--input", type=Path, required=True, help="规范化 Markdown 根目录")
    parser.add_argument("--output", type=Path, required=True, help="chunks.jsonl 输出路径")
    parser.add_argument("--max-chars", type=int, default=1200, help="单个正文块的最大字符数")
    parser.add_argument("--overlap-chars", type=int, default=150, help="相邻块的最大重叠字符数")
    return parser


def main() -> None:
    """执行目录切分并在终端显示核心质量统计。"""
    args = build_parser().parse_args()
    config = ChunkingConfig(max_chars=args.max_chars, overlap_chars=args.overlap_chars)
    report = chunk_normalized_directory(args.input, args.output, config)
    print(
        f"切分完成：{report['document_count']} 个文档，"
        f"{report['chunk_count']} 个文本块，最大长度 {report['max_chunk_chars']} 字符"
    )
    print(f"输出文件：{args.output.resolve()}")


if __name__ == "__main__":
    main()

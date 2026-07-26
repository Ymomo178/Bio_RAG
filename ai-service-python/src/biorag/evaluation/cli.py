"""检索评测集校验命令行入口。"""

import argparse
from pathlib import Path

from biorag.evaluation.retrieval_dataset import validate_retrieval_dataset


def build_parser() -> argparse.ArgumentParser:
    """创建评测集校验命令的参数解析器。"""
    parser = argparse.ArgumentParser(description="校验检索问题能否定位到当前 RAG 文本块")
    parser.add_argument("--dataset", type=Path, required=True, help="检索问题 JSONL 路径")
    parser.add_argument("--chunks", type=Path, required=True, help="chunks.jsonl 路径")
    parser.add_argument("--output", type=Path, help="解析后的标准文本块报告路径")
    return parser


def main() -> None:
    """执行证据定位，并在存在未解析问题时返回失败状态。"""
    args = build_parser().parse_args()
    report = validate_retrieval_dataset(args.dataset, args.chunks, args.output)
    print(
        f"评测集校验完成：{report['resolved_question_count']}/"
        f"{report['question_count']} 个问题已定位到原文文本块"
    )
    if report["unresolved_question_ids"]:
        unresolved = ", ".join(report["unresolved_question_ids"])
        raise SystemExit(f"以下问题没有定位到证据：{unresolved}")


if __name__ == "__main__":
    main()

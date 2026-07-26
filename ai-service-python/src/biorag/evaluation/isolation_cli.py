"""检查有答案集、无答案集和独立测试集的隔离状态。"""

import argparse
import json
from pathlib import Path

from biorag.evaluation.no_answer_dataset import validate_evaluation_isolation


def main() -> None:
    """执行评测集隔离检查并写入 JSON 报告。"""
    parser = argparse.ArgumentParser(description="检查 Bio-RAG 评测集是否相互隔离")
    parser.add_argument("--development", type=Path, required=True, help="有答案开发集")
    parser.add_argument("--test", type=Path, required=True, help="有答案独立测试集")
    parser.add_argument("--chunks", type=Path, required=True, help="文本块 JSONL")
    parser.add_argument("--no-answer-development", type=Path, help="无答案开发集")
    parser.add_argument("--no-answer-test", type=Path, help="无答案独立测试集")
    parser.add_argument("--output", type=Path, required=True, help="隔离报告 JSON")
    args = parser.parse_args()
    report = validate_evaluation_isolation(
        args.development,
        args.test,
        args.chunks,
        args.no_answer_development,
        args.no_answer_test,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    if not report["isolated"]:
        raise SystemExit("评测集没有完全隔离")


if __name__ == "__main__":
    main()

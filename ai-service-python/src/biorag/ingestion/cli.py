"""文档规范化命令行入口。"""

import argparse
from pathlib import Path

from biorag.ingestion.pipeline import normalize_manifest, preview_manifest


def build_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器。"""
    parser = argparse.ArgumentParser(description="筛选并规范化 Bio-RAG 官方文档")
    parser.add_argument("--manifest", type=Path, required=True, help="sources.yml 的路径")
    parser.add_argument("--output", type=Path, help="规范化 Markdown 输出目录")
    parser.add_argument("--dry-run", action="store_true", help="只预览白名单，不写文件")
    return parser


def main() -> None:
    """执行白名单预览或完整规范化任务。"""
    args = build_parser().parse_args()
    if args.dry_run:
        preview = preview_manifest(args.manifest)
        for source_id, paths in preview.items():
            print(f"{source_id}: {len(paths)} 个文件")
            for path in paths:
                print(f"  - {path}")
        return
    if args.output is None:
        raise SystemExit("非 dry-run 模式必须提供 --output")
    records = normalize_manifest(args.manifest, args.output)
    print(f"规范化完成：{len(records)} 个文档，输出目录：{args.output.resolve()}")


if __name__ == "__main__":
    main()

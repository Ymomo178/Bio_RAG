"""将本地文本块和向量索引导入 PostgreSQL + pgvector。"""

import argparse
import json
from pathlib import Path
from uuid import UUID

from biorag.retrieval.dense import DenseIndex
from biorag.retrieval.postgres import PostgresChunkStore


def main() -> None:
    """读取本地索引并批量写入指定 PostgreSQL 知识库。"""
    parser = argparse.ArgumentParser(description="把本地 BGE-M3 索引导入 PostgreSQL + pgvector")
    parser.add_argument("--index", type=Path, required=True, help="本地向量索引目录")
    parser.add_argument("--connection", required=True, help="PostgreSQL 连接字符串")
    parser.add_argument("--knowledge-base-id", type=UUID, help="可选的业务知识库 UUID")
    parser.add_argument("--document-version-id", type=UUID, help="可选的文档版本 UUID")
    args = parser.parse_args()

    index = DenseIndex.load(args.index)
    manifest = json.loads((args.index / "manifest.json").read_text(encoding="utf-8"))
    store = PostgresChunkStore(args.connection)
    try:
        count = store.upsert_chunks(
            index.chunks,
            index.embeddings,
            model_name=str(manifest["model_name"]),
            knowledge_base_id=args.knowledge_base_id,
            document_version_id=args.document_version_id,
        )
    finally:
        store.close()
    print(f"已导入 {count} 个文本块，模型：{manifest['model_name']}")


if __name__ == "__main__":
    main()

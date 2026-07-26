"""PostgreSQL + pgvector 的文本块存储和混合召回实现。"""

import os
from collections.abc import Iterable
from typing import Any
from uuid import UUID

import numpy as np

from biorag.retrieval.dense import SearchResult
from biorag.retrieval.hybrid import HybridSearchConfig, ResultReranker


class PostgresChunkStore:
    """把文本块、元数据和 1024 维向量保存到 PostgreSQL。"""

    def __init__(self, connection_string: str) -> None:
        """建立数据库连接并注册 pgvector 的 Python 类型适配器。"""
        try:
            import psycopg
            from pgvector.psycopg import register_vector
            from psycopg.rows import dict_row
        except ImportError as error:
            raise RuntimeError("请安装数据库服务依赖：pip install -e '.[service]'") from error
        self._connection = psycopg.connect(
            connection_string,
            row_factory=dict_row,
            connect_timeout=int(os.getenv("DATABASE_CONNECT_TIMEOUT_SECONDS", "5")),
        )
        register_vector(self._connection)

    def close(self) -> None:
        """关闭数据库连接。"""
        self._connection.close()

    def healthcheck(self) -> bool:
        """执行简单查询确认数据库连接和 RAG schema 可用。"""
        with self._connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM rag.document_chunks LIMIT 1")
        return True

    def upsert_chunks(
        self,
        chunks: list[dict[str, Any]],
        embeddings: np.ndarray,
        model_name: str,
        knowledge_base_id: UUID | None = None,
        document_version_id: UUID | None = None,
    ) -> int:
        """批量写入文本块，重复 chunk_id 时更新内容和向量。"""
        vectors = np.asarray(embeddings, dtype=np.float32)
        if vectors.ndim != 2 or vectors.shape[0] != len(chunks) or vectors.shape[1] != 1024:
            raise ValueError("文本块数量和向量必须匹配，且向量维度必须为 1024")
        sql = """
            INSERT INTO rag.document_chunks (
                chunk_id, knowledge_base_id, document_version_id, chunk_index,
                source_id, normalized_path, document_title, section, page_number,
                content, embedding_text, image_ids, metadata, model_name, embedding
            ) VALUES (
                %(chunk_id)s, %(knowledge_base_id)s, %(document_version_id)s, %(chunk_index)s,
                %(source_id)s, %(normalized_path)s, %(document_title)s, %(section)s, %(page_number)s,
                %(content)s, %(embedding_text)s, %(image_ids)s, %(metadata)s, %(model_name)s, %(embedding)s
            )
            ON CONFLICT (chunk_id) DO UPDATE SET
                knowledge_base_id = EXCLUDED.knowledge_base_id,
                document_version_id = EXCLUDED.document_version_id,
                chunk_index = EXCLUDED.chunk_index,
                source_id = EXCLUDED.source_id,
                normalized_path = EXCLUDED.normalized_path,
                document_title = EXCLUDED.document_title,
                section = EXCLUDED.section,
                page_number = EXCLUDED.page_number,
                content = EXCLUDED.content,
                embedding_text = EXCLUDED.embedding_text,
                image_ids = EXCLUDED.image_ids,
                metadata = EXCLUDED.metadata,
                model_name = EXCLUDED.model_name,
                embedding = EXCLUDED.embedding,
                updated_at = CURRENT_TIMESTAMP
        """
        try:
            from psycopg.types.json import Json
        except ImportError as error:
            raise RuntimeError("请安装 psycopg：pip install -e '.[service]'") from error
        records = [
            {
                "chunk_id": str(chunk["chunk_id"]),
                "knowledge_base_id": knowledge_base_id,
                "document_version_id": document_version_id,
                "chunk_index": int(chunk.get("chunk_index", 0)),
                "source_id": str(chunk.get("source_id", "")),
                "normalized_path": str(chunk.get("normalized_path", "")),
                "document_title": chunk.get("document_title"),
                "section": chunk.get("section"),
                "page_number": chunk.get("page_number"),
                "content": str(chunk.get("content", "")),
                "embedding_text": str(chunk.get("embedding_text", chunk.get("content", ""))),
                "image_ids": Json(chunk.get("image_ids", [])),
                "metadata": Json(chunk),
                "model_name": model_name,
                "embedding": vectors[index],
            }
            for index, chunk in enumerate(chunks)
        ]
        with self._connection.cursor() as cursor:
            cursor.executemany(sql, records)
        self._connection.commit()
        return len(records)

    def search_dense(
        self,
        query_vector: np.ndarray,
        top_k: int,
        knowledge_base_ids: list[UUID] | None = None,
    ) -> list[SearchResult]:
        """使用 pgvector 余弦距离执行稠密向量召回。"""
        if top_k <= 0:
            raise ValueError("top_k 必须大于 0")
        vector = np.asarray(query_vector, dtype=np.float32).reshape(-1)
        if vector.shape[0] != 1024:
            raise ValueError("查询向量维度必须为 1024")
        where_sql, params = _knowledge_base_filter(knowledge_base_ids)
        sql = f"""
            SELECT *, 1 - (embedding <=> %s) AS score
            FROM rag.document_chunks
            {where_sql}
            ORDER BY embedding <=> %s
            LIMIT %s
        """
        query_params = [vector, *params, vector, top_k]
        with self._connection.cursor() as cursor:
            cursor.execute(sql, query_params)
            rows = cursor.fetchall()
        return [_row_to_result(row) for row in rows]

    def search_keyword(
        self,
        query: str,
        top_k: int,
        knowledge_base_ids: list[UUID] | None = None,
    ) -> list[SearchResult]:
        """使用 PostgreSQL simple 分词和 GIN 全文索引执行关键词召回。"""
        if top_k <= 0:
            raise ValueError("top_k 必须大于 0")
        where_sql, params = _knowledge_base_filter(knowledge_base_ids)
        sql = f"""
            WITH query AS (SELECT plainto_tsquery('simple', %s) AS value)
            SELECT chunks.*, ts_rank_cd(chunks.search_vector, query.value) AS score
            FROM rag.document_chunks AS chunks, query
            WHERE chunks.search_vector @@ query.value
            {where_sql.replace('WHERE', 'AND', 1) if where_sql else ''}
            ORDER BY score DESC
            LIMIT %s
        """
        with self._connection.cursor() as cursor:
            cursor.execute(sql, [query, *params, top_k])
            rows = cursor.fetchall()
        return [_row_to_result(row) for row in rows]


class PostgresHybridRetriever:
    """在 PostgreSQL 中融合 pgvector、全文检索和 Reranker。"""

    def __init__(
        self,
        store: PostgresChunkStore,
        embedder: Any,
        reranker: ResultReranker | None = None,
        config: HybridSearchConfig | None = None,
    ) -> None:
        """组合数据库存储、Embedding 模型和可选重排序模型。"""
        self.store = store
        self.embedder = embedder
        self.reranker = reranker
        self.config = config or HybridSearchConfig()

    def search(
        self,
        query: str,
        top_k: int,
        knowledge_base_ids: list[UUID] | None = None,
    ) -> list[SearchResult]:
        """执行两路数据库召回、RRF 融合和最终重排序。"""
        if top_k <= 0:
            raise ValueError("top_k 必须大于 0")
        query_vector = self.embedder.encode_queries([query])[0]
        dense_results = self.store.search_dense(
            query_vector,
            self.config.dense_candidate_count,
            knowledge_base_ids,
        )
        keyword_results = self.store.search_keyword(
            query,
            self.config.keyword_candidate_count,
            knowledge_base_ids,
        )
        fused = _fuse_results(dense_results, keyword_results, self.config)
        if self.reranker is None:
            return fused[:top_k]
        return self.reranker.rerank(
            query,
            fused[: max(top_k, self.config.rerank_candidate_count)],
            top_k,
        )


def _knowledge_base_filter(
    knowledge_base_ids: list[UUID] | None,
) -> tuple[str, list[object]]:
    """生成知识库过滤条件；空列表只允许检索旧版内置文本块。"""
    if knowledge_base_ids is None:
        return "", []
    if not knowledge_base_ids:
        return "WHERE knowledge_base_id IS NULL", []
    return "WHERE knowledge_base_id = ANY(%s)", [knowledge_base_ids]


def _row_to_result(row: dict[str, Any]) -> SearchResult:
    """将 PostgreSQL 行转换为现有检索结果对象。"""
    chunk = {
        "chunk_id": row["chunk_id"],
        "chunk_index": row["chunk_index"],
        "source_id": row["source_id"],
        "normalized_path": row["normalized_path"],
        "document_title": row["document_title"],
        "section": row["section"],
        "page_number": row["page_number"],
        "content": row["content"],
        "embedding_text": row["embedding_text"],
        "image_ids": row["image_ids"],
        "metadata": row["metadata"],
    }
    return SearchResult(str(row["chunk_id"]), float(row["score"]), chunk)


def _fuse_results(
    dense_results: list[SearchResult],
    keyword_results: list[SearchResult],
    config: HybridSearchConfig,
) -> list[SearchResult]:
    """使用 RRF 合并 PostgreSQL 返回的两份排名。"""
    scores: dict[str, float] = {}
    chunks: dict[str, dict[str, Any]] = {}
    for results, weight in (
        (dense_results, config.dense_weight),
        (keyword_results, config.keyword_weight),
    ):
        for rank, result in enumerate(results, start=1):
            scores[result.chunk_id] = scores.get(result.chunk_id, 0.0) + weight / (
                config.rrf_k + rank
            )
            chunks[result.chunk_id] = result.chunk
    ordered_ids = sorted(scores, key=lambda chunk_id: (-scores[chunk_id], chunk_id))
    return [SearchResult(chunk_id, scores[chunk_id], chunks[chunk_id]) for chunk_id in ordered_ids]

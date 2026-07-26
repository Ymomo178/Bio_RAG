"""BM25、RRF 混合检索和重排序候选流程测试。"""

import numpy as np

from biorag.retrieval.dense import DenseIndex, SearchResult
from biorag.retrieval.hybrid import BM25KeywordIndex, HybridRetriever, HybridSearchConfig
from biorag.retrieval.postgres import _knowledge_base_filter
from uuid import uuid4


class FakeEmbedder:
    """让测试问题固定偏向语义干扰块。"""

    model_name = "fake"
    max_sequence_length = 10

    def encode_queries(self, texts: list[str]) -> np.ndarray:
        """所有问题都返回第一维向量。"""
        return np.asarray([[1.0, 0.0] for _ in texts], dtype=np.float32)

    def encode_passages(self, texts: list[str]) -> np.ndarray:
        """测试不需要重新构建稠密索引。"""
        raise NotImplementedError

    def count_tokens(self, texts: list[str]) -> list[int]:
        """测试不需要统计 Token。"""
        return [len(text) for text in texts]


class FakeReranker:
    """把包含“正确答案”的候选稳定排在第一名。"""

    model_name = "fake-reranker"
    device = "cpu"
    precision = "float32"

    def rerank(self, query: str, candidates: list[SearchResult], top_k: int) -> list[SearchResult]:
        """模拟交叉编码器识别真正回答问题的段落。"""
        ordered = sorted(candidates, key=lambda item: "正确答案" not in str(item.chunk["content"]))
        return ordered[:top_k]


def _chunks() -> list[dict[str, object]]:
    """创建一个语义干扰块、一个精确参数块和一个无关块。"""
    return [
        {
            "chunk_id": "semantic",
            "embedding_text": "Cutadapt minimum overlap adapter matching",
            "content": "介绍 adapter 的最小重叠长度。",
        },
        {
            "chunk_id": "keyword",
            "embedding_text": "Cutadapt --minimum-length discards short reads",
            "content": "正确答案：--minimum-length 丢弃过短 reads。",
        },
        {
            "chunk_id": "other",
            "embedding_text": "Salmon transcript abundance",
            "content": "无关内容。",
        },
    ]


def test_bm25_keyword_index_preserves_cli_option() -> None:
    """带连字符的完整命令参数应能通过 BM25 精确召回。"""
    index = BM25KeywordIndex(_chunks())

    results = index.search("Cutadapt 的 --minimum-length 有什么作用？", 3)

    assert results[0].chunk_id == "keyword"


def test_hybrid_retrieval_and_reranker_recover_keyword_answer() -> None:
    """即使稠密检索偏向干扰块，关键词召回和重排序也应恢复正确答案。"""
    chunks = _chunks()
    dense_index = DenseIndex(
        model_name="fake",
        chunks=chunks,
        embeddings=np.asarray([[1.0, 0.0], [0.0, 1.0], [0.0, 1.0]], dtype=np.float32),
    )
    retriever = HybridRetriever(
        dense_index=dense_index,
        embedder=FakeEmbedder(),
        keyword_index=BM25KeywordIndex(chunks),
        reranker=FakeReranker(),
        config=HybridSearchConfig(
            dense_candidate_count=3,
            keyword_candidate_count=3,
            rerank_candidate_count=3,
        ),
    )

    results = retriever.search("Cutadapt 的 --minimum-length 有什么作用？", 1)

    assert results[0].chunk_id == "keyword"


def test_postgres_filter_supports_multiple_knowledge_bases() -> None:
    """多选知识库应生成 ANY 过滤，空选择只检索旧版内置文本块。"""
    ids = [uuid4(), uuid4()]

    where_sql, params = _knowledge_base_filter(ids)
    built_in_sql, built_in_params = _knowledge_base_filter([])

    assert "ANY" in where_sql
    assert params == [ids]
    assert built_in_sql == "WHERE knowledge_base_id IS NULL"
    assert built_in_params == []

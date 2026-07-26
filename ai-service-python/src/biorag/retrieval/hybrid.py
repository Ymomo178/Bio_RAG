"""组合 BM25、稠密向量和交叉编码器重排序的混合检索。"""

import re
from dataclasses import dataclass
from typing import Protocol

import numpy as np

from biorag.retrieval.dense import DenseIndex, SearchResult, TextEmbedder

_LATIN_TOKEN_PATTERN = re.compile(r"--?[A-Za-z0-9][A-Za-z0-9_-]*|[A-Za-z0-9][A-Za-z0-9_.:/]*")
_CHINESE_PATTERN = re.compile(r"[\u4e00-\u9fff]+")


class ResultReranker(Protocol):
    """约束重排序模型需要提供的最小接口。"""

    model_name: str
    device: str
    precision: str

    def rerank(self, query: str, candidates: list[SearchResult], top_k: int) -> list[SearchResult]:
        """根据问题与候选原文的相关性重新排序。"""
        ...


@dataclass(frozen=True)
class HybridSearchConfig:
    """保存混合检索的候选数量和 RRF 融合权重。"""

    dense_candidate_count: int = 50
    keyword_candidate_count: int = 50
    rerank_candidate_count: int = 100
    rrf_k: int = 60
    dense_weight: float = 1.0
    keyword_weight: float = 1.0

    def __post_init__(self) -> None:
        """拒绝会导致空候选集或无效融合分数的配置。"""
        integer_values = (
            self.dense_candidate_count,
            self.keyword_candidate_count,
            self.rerank_candidate_count,
            self.rrf_k,
        )
        if any(value <= 0 for value in integer_values):
            raise ValueError("候选数量和 rrf_k 必须大于 0")
        if self.dense_weight < 0 or self.keyword_weight < 0:
            raise ValueError("检索权重不能小于 0")
        if self.dense_weight == 0 and self.keyword_weight == 0:
            raise ValueError("稠密检索和关键词检索不能同时关闭")


class BM25KeywordIndex:
    """使用 BM25 为命令参数、文件名和专业术语提供精确关键词检索。"""

    def __init__(self, chunks: list[dict[str, object]]) -> None:
        """对文本块建立轻量内存索引，当前数据规模无需单独数据库。"""
        try:
            from rank_bm25 import BM25Okapi
        except ImportError as error:
            raise RuntimeError("请安装混合检索依赖：pip install -e '.[embedding]'") from error
        self.chunks = chunks
        corpus = [_tokenize(str(chunk.get("embedding_text") or chunk.get("content") or "")) for chunk in chunks]
        self._index = BM25Okapi(corpus)

    def search(self, query: str, top_k: int) -> list[SearchResult]:
        """返回 BM25 分数为正的前 K 个文本块，避免无关键词命中时引入噪声。"""
        if top_k <= 0:
            raise ValueError("top_k 必须大于 0")
        tokens = _tokenize(query)
        if not tokens:
            return []
        scores = np.asarray(self._index.get_scores(tokens), dtype=np.float32)
        indices = np.argsort(-scores, kind="stable")
        results: list[SearchResult] = []
        for index in indices:
            score = float(scores[index])
            if score <= 0:
                break
            chunk = self.chunks[int(index)]
            results.append(SearchResult(str(chunk["chunk_id"]), score, chunk))
            if len(results) >= top_k:
                break
        return results


class CrossEncoderReranker:
    """使用 BGE 交叉编码器直接判断问题与候选段落是否相关。"""

    def __init__(
        self,
        model_name: str = "BAAI/bge-reranker-v2-m3",
        device: str | None = None,
        batch_size: int = 4,
        max_length: int = 1024,
    ) -> None:
        """加载重排序模型，并在 CUDA 上切换为半精度以节省显存。"""
        try:
            from sentence_transformers import CrossEncoder
        except ImportError as error:
            raise RuntimeError("请安装 Embedding 依赖：pip install -e '.[embedding]'") from error
        self.model_name = model_name
        self.batch_size = batch_size
        self._model = CrossEncoder(model_name, device=device, max_length=max_length)
        self.device = str(next(self._model.model.parameters()).device)
        if self.device.startswith("cuda"):
            self._model.model.half()
            self.precision = "float16"
        else:
            self.precision = "float32"

    def rerank(self, query: str, candidates: list[SearchResult], top_k: int) -> list[SearchResult]:
        """批量计算问题与候选段落的相关性分数，并返回最高分结果。"""
        if top_k <= 0:
            raise ValueError("top_k 必须大于 0")
        if not candidates:
            return []
        pairs = [
            (query, str(candidate.chunk.get("embedding_text") or candidate.chunk.get("content") or ""))
            for candidate in candidates
        ]
        scores = np.asarray(
            self._model.predict(
                pairs,
                batch_size=self.batch_size,
                convert_to_numpy=True,
                show_progress_bar=False,
            ),
            dtype=np.float32,
        ).reshape(-1)
        order = np.argsort(-scores, kind="stable")[:top_k]
        return [
            SearchResult(
                chunk_id=candidates[int(index)].chunk_id,
                score=float(scores[int(index)]),
                chunk=candidates[int(index)].chunk,
            )
            for index in order
        ]


class HybridRetriever:
    """融合 BGE-M3 语义召回、BM25 精确召回和可选重排序。"""

    def __init__(
        self,
        dense_index: DenseIndex,
        embedder: TextEmbedder,
        keyword_index: BM25KeywordIndex,
        reranker: ResultReranker | None = None,
        config: HybridSearchConfig | None = None,
    ) -> None:
        """组合检索组件，并保留可单独关闭重排序的评测能力。"""
        self.dense_index = dense_index
        self.embedder = embedder
        self.keyword_index = keyword_index
        self.reranker = reranker
        self.config = config or HybridSearchConfig()

    def search(self, query: str, top_k: int) -> list[SearchResult]:
        """分别召回候选，使用 RRF 融合后按需执行交叉编码器重排序。"""
        if top_k <= 0:
            raise ValueError("top_k 必须大于 0")
        query_vector = self.embedder.encode_queries([query])[0]
        dense_results = self.dense_index.search(query_vector, self.config.dense_candidate_count)
        keyword_results = self.keyword_index.search(query, self.config.keyword_candidate_count)
        fused = self._fuse_results(dense_results, keyword_results)
        if self.reranker is None:
            return fused[:top_k]
        candidates = fused[: max(top_k, self.config.rerank_candidate_count)]
        return self.reranker.rerank(query, candidates, top_k)

    def _fuse_results(
        self,
        dense_results: list[SearchResult],
        keyword_results: list[SearchResult],
    ) -> list[SearchResult]:
        """使用倒数排名融合，避免直接比较余弦分数和 BM25 分数。"""
        scores: dict[str, float] = {}
        chunks: dict[str, dict[str, object]] = {}
        ranked_groups = (
            (dense_results, self.config.dense_weight),
            (keyword_results, self.config.keyword_weight),
        )
        for results, weight in ranked_groups:
            for rank, result in enumerate(results, start=1):
                scores[result.chunk_id] = scores.get(result.chunk_id, 0.0) + weight / (
                    self.config.rrf_k + rank
                )
                chunks[result.chunk_id] = result.chunk
        ordered_ids = sorted(scores, key=lambda chunk_id: (-scores[chunk_id], chunk_id))
        return [
            SearchResult(chunk_id, scores[chunk_id], chunks[chunk_id])
            for chunk_id in ordered_ids
        ]


def _tokenize(text: str) -> list[str]:
    """保留命令参数和文件名，并为中文补充单字与双字词元。"""
    lowered = text.lower()
    tokens = _LATIN_TOKEN_PATTERN.findall(lowered)
    for sequence in _CHINESE_PATTERN.findall(lowered):
        tokens.extend(sequence)
        tokens.extend(sequence[index : index + 2] for index in range(len(sequence) - 1))
    return tokens

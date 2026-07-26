"""构建本地稠密向量索引并执行余弦相似度检索。"""

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

import numpy as np


class TextEmbedder(Protocol):
    """约束向量模型必须提供的最小接口，便于测试和后续替换模型。"""

    model_name: str
    max_sequence_length: int

    def encode_queries(self, texts: list[str]) -> np.ndarray:
        """把检索问题转换为已归一化向量。"""
        ...

    def encode_passages(self, texts: list[str]) -> np.ndarray:
        """把知识库文本块转换为已归一化向量。"""
        ...

    def count_tokens(self, texts: list[str]) -> list[int]:
        """返回每段文本在当前模型 Tokenizer 下的 Token 数。"""
        ...


class SentenceTransformerEmbedder:
    """使用 Sentence Transformers 加载本地或 Hugging Face Embedding 模型。"""

    def __init__(
        self,
        model_name: str = "BAAI/bge-m3",
        device: str | None = None,
        batch_size: int = 8,
    ) -> None:
        """加载模型，并根据模型类型配置前缀和半精度推理。"""
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as error:
            raise RuntimeError("请先安装项目的 embedding 可选依赖：pip install -e '.[embedding]'") from error
        self.model_name = model_name
        self.batch_size = batch_size
        model_key = model_name.lower()
        self._query_prefix = "query: " if "e5" in model_key else ""
        self._passage_prefix = "passage: " if "e5" in model_key else ""
        local_files_only = os.getenv("MODEL_LOCAL_FILES_ONLY", "false").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        self._model = SentenceTransformer(
            model_name,
            device=device,
            local_files_only=local_files_only,
        )
        if str(self._model.device).startswith("cuda"):
            self._model.half()
            self.precision = "float16"
        else:
            self.precision = "float32"
        self.device = str(self._model.device)
        self.max_sequence_length = int(self._model.max_seq_length)

    def encode_queries(self, texts: list[str]) -> np.ndarray:
        """按照当前模型约定编码用户问题。"""
        return self._encode([f"{self._query_prefix}{text}" for text in texts])

    def encode_passages(self, texts: list[str]) -> np.ndarray:
        """按照当前模型约定编码知识库文本。"""
        return self._encode([f"{self._passage_prefix}{text}" for text in texts])

    def count_tokens(self, texts: list[str]) -> list[int]:
        """在不截断的情况下统计模型实际输入的 Token 数。"""
        prefixed = [f"{self._passage_prefix}{text}" for text in texts]
        encoded = self._model.tokenizer(prefixed, add_special_tokens=True, truncation=False)
        return [len(token_ids) for token_ids in encoded["input_ids"]]

    def _encode(self, texts: list[str]) -> np.ndarray:
        """批量编码并归一化，使向量点积等价于余弦相似度。"""
        vectors = self._model.encode(
            texts,
            batch_size=self.batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=len(texts) > self.batch_size,
        )
        return np.asarray(vectors, dtype=np.float32)


@dataclass(frozen=True)
class SearchResult:
    """表示一条向量检索命中的文本块及相似度。"""

    chunk_id: str
    score: float
    chunk: dict[str, Any]


@dataclass
class DenseIndex:
    """在内存中保存文本块和对应的归一化稠密向量。"""

    model_name: str
    chunks: list[dict[str, Any]]
    embeddings: np.ndarray

    def __post_init__(self) -> None:
        """检查文本块数量、向量形状和数据类型。"""
        self.embeddings = np.asarray(self.embeddings, dtype=np.float32)
        if self.embeddings.ndim != 2:
            raise ValueError("embeddings 必须是二维矩阵")
        if len(self.chunks) != self.embeddings.shape[0]:
            raise ValueError("文本块数量与向量数量不一致")

    def search(self, query_vector: np.ndarray, top_k: int) -> list[SearchResult]:
        """使用归一化向量点积返回分数最高的文本块。"""
        if top_k <= 0:
            raise ValueError("top_k 必须大于 0")
        vector = np.asarray(query_vector, dtype=np.float32).reshape(-1)
        if vector.shape[0] != self.embeddings.shape[1]:
            raise ValueError("查询向量维度与索引维度不一致")
        result_count = min(top_k, len(self.chunks))
        scores = self.embeddings @ vector
        indices = np.argsort(-scores, kind="stable")[:result_count]
        return [
            SearchResult(
                chunk_id=str(self.chunks[index]["chunk_id"]),
                score=float(scores[index]),
                chunk=self.chunks[index],
            )
            for index in indices
        ]

    def save(self, index_directory: Path, manifest: dict[str, Any]) -> None:
        """把向量矩阵、文本块元数据和构建清单写入本地目录。"""
        index_directory.mkdir(parents=True, exist_ok=True)
        np.save(index_directory / "embeddings.npy", self.embeddings, allow_pickle=False)
        with (index_directory / "chunks.jsonl").open("w", encoding="utf-8", newline="\n") as chunks_file:
            for chunk in self.chunks:
                chunks_file.write(json.dumps(chunk, ensure_ascii=False) + "\n")
        (index_directory / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    @classmethod
    def load(cls, index_directory: Path) -> "DenseIndex":
        """从本地文件恢复向量索引。"""
        manifest = json.loads((index_directory / "manifest.json").read_text(encoding="utf-8"))
        chunks = _load_jsonl(index_directory / "chunks.jsonl")
        embeddings = np.load(index_directory / "embeddings.npy", allow_pickle=False)
        return cls(model_name=str(manifest["model_name"]), chunks=chunks, embeddings=embeddings)


def build_dense_index(
    chunks_path: Path,
    index_directory: Path,
    embedder: TextEmbedder,
) -> tuple[DenseIndex, dict[str, Any]]:
    """编码全部文本块、统计 Token 长度并保存可复用的本地索引。"""
    chunks = _load_jsonl(chunks_path)
    if not chunks:
        raise ValueError(f"文本块文件不能为空：{chunks_path}")
    passages = [str(chunk["embedding_text"]) for chunk in chunks]
    token_lengths = embedder.count_tokens(passages)
    embeddings = embedder.encode_passages(passages)
    index = DenseIndex(embedder.model_name, chunks, embeddings)
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model_name": embedder.model_name,
        "max_sequence_length": embedder.max_sequence_length,
        "embedding_dimension": int(embeddings.shape[1]),
        "chunk_count": len(chunks),
        "chunks_sha256": _sha256(chunks_path),
        "token_statistics": _token_statistics(token_lengths, embedder.max_sequence_length),
    }
    index.save(index_directory, manifest)
    return index, manifest


def load_or_build_dense_index(
    chunks_path: Path,
    index_directory: Path,
    embedder: TextEmbedder,
) -> tuple[DenseIndex, dict[str, Any], bool]:
    """在模型和文本块未变化时复用索引，否则重新生成。"""
    manifest_path = index_directory / "manifest.json"
    expected_hash = _sha256(chunks_path)
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("model_name") == embedder.model_name and manifest.get("chunks_sha256") == expected_hash:
            return DenseIndex.load(index_directory), manifest, False
    index, manifest = build_dense_index(chunks_path, index_directory, embedder)
    return index, manifest, True


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    """读取逐行 JSON 对象。"""
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as input_file:
        for line_number, line in enumerate(input_file, start=1):
            if not line.strip():
                continue
            payload = json.loads(line)
            if not isinstance(payload, dict):
                raise ValueError(f"{path} 第 {line_number} 行必须是 JSON 对象")
            records.append(payload)
    return records


def _token_statistics(token_lengths: list[int], max_sequence_length: int) -> dict[str, int | float]:
    """汇总 Token 长度分布和会被模型截断的文本块数量。"""
    values = np.asarray(token_lengths, dtype=np.int32)
    return {
        "minimum": int(values.min()),
        "median": int(np.percentile(values, 50)),
        "p90": int(np.percentile(values, 90)),
        "p95": int(np.percentile(values, 95)),
        "maximum": int(values.max()),
        "average": round(float(values.mean()), 2),
        "over_model_limit": int(np.sum(values > max_sequence_length)),
    }


def _sha256(path: Path) -> str:
    """计算输入文件哈希，用于判断本地索引是否已经过期。"""
    digest = hashlib.sha256()
    with path.open("rb") as input_file:
        for block in iter(lambda: input_file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()

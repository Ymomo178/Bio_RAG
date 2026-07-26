"""处理由 Java 后端保存的单个用户上传文档。"""

import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

import yaml

from biorag.ingestion.chunking import ChunkingConfig, chunk_markdown_document
from biorag.ingestion.normalizers import normalize_file


@dataclass(frozen=True)
class UploadIndexResult:
    """表示一份上传文档完成索引后的统计结果。"""

    chunk_count: int
    image_count: int
    document_title: str


def index_uploaded_document(
    source_path: Path,
    original_filename: str,
    knowledge_base_id: UUID,
    document_version_id: UUID,
    artifact_root: Path,
    embedder: Any,
    store: Any,
) -> UploadIndexResult:
    """规范化单个文件、切分、向量化并写入指定知识库。"""
    source_path = source_path.resolve()
    if not source_path.is_file():
        raise ValueError(f"上传文件不存在：{source_path}")

    work_directory = artifact_root.resolve() / str(document_version_id)
    work_directory.mkdir(parents=True, exist_ok=True)
    normalized = normalize_file(source_path, Path(original_filename).stem, source_path.parent)
    source_id = f"upload-{document_version_id}"
    source_hash = _sha256(source_path)
    markdown, image_ids = _write_images(
        normalized.markdown,
        normalized.images,
        work_directory,
        source_id,
    )
    metadata = {
        "source_id": source_id,
        "tool": "user-upload",
        "title": normalized.title,
        "source_url": "",
        "source_path": original_filename,
        "source_sha256": source_hash,
        "image_count": len(image_ids),
        "image_ids": image_ids,
    }
    normalized_path = work_directory / "document.md"
    normalized_path.write_text(
        _with_front_matter(metadata, markdown),
        encoding="utf-8",
    )
    chunks = chunk_markdown_document(
        normalized_path,
        work_directory,
        ChunkingConfig(),
    )
    if not chunks:
        raise ValueError("文档没有可用于检索的文字内容")
    chunk_records = [asdict(chunk) for chunk in chunks]
    embeddings = embedder.encode_passages(
        [str(chunk["embedding_text"]) for chunk in chunk_records]
    )
    store.upsert_chunks(
        chunk_records,
        embeddings,
        model_name=str(embedder.model_name),
        knowledge_base_id=knowledge_base_id,
        document_version_id=document_version_id,
    )
    return UploadIndexResult(
        chunk_count=len(chunk_records),
        image_count=len(image_ids),
        document_title=normalized.title,
    )


def _write_images(
    markdown: str,
    images: tuple[Any, ...],
    work_directory: Path,
    source_id: str,
) -> tuple[str, list[str]]:
    """保存解析出的位图，并把 Markdown 占位符替换成稳定图片 ID。"""
    image_ids: list[str] = []
    asset_directory = work_directory / "assets"
    for index, image in enumerate(images, start=1):
        image_id = f"{source_id}-image-{index:04d}"
        image_ids.append(image_id)
        markdown = markdown.replace(
            image.placeholder,
            f"![{image.caption}](asset://{image_id})",
        )
        if image.content is None:
            continue
        extension = Path(image.filename).suffix.lower()
        if extension not in {
            ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".bmp", ".tif", ".tiff"
        }:
            extension = ".bin"
        asset_directory.mkdir(parents=True, exist_ok=True)
        (asset_directory / f"{image_id}{extension}").write_bytes(image.content)
    return markdown, image_ids


def _with_front_matter(metadata: dict[str, object], markdown: str) -> str:
    """为上传文档写入切分器需要的 YAML 来源信息。"""
    front_matter = yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False).strip()
    return f"---\n{front_matter}\n---\n\n{markdown}"


def _sha256(path: Path) -> str:
    """流式计算上传文件哈希。"""
    digest = hashlib.sha256()
    with path.open("rb") as input_file:
        for block in iter(lambda: input_file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()

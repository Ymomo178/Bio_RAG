"""组织来源筛选、格式转换和报告生成。"""

import hashlib
import json
import mimetypes
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import yaml

from biorag.ingestion.manifest import discover_source_files, load_sources
from biorag.ingestion.models import ExtractedImage, ImageManifestRecord, NormalizationRecord, SourceSpec
from biorag.ingestion.normalizers import normalize_file


def preview_manifest(manifest_path: Path) -> dict[str, list[str]]:
    """只执行白名单选择，返回每个来源将要处理的文件。"""
    preview: dict[str, list[str]] = {}
    for source in load_sources(manifest_path):
        preview[source.source_id] = [str(path) for path in discover_source_files(source)]
    return preview


def normalize_manifest(manifest_path: Path, output_root: Path) -> list[NormalizationRecord]:
    """处理清单中的全部白名单文件，并写出 Markdown 和 JSON 报告。"""
    manifest_path = manifest_path.resolve()
    repository_root = manifest_path.parent.parent
    output_root = output_root.resolve()
    records: list[NormalizationRecord] = []
    image_records: list[ImageManifestRecord] = []

    for source in load_sources(manifest_path):
        for input_path in discover_source_files(source):
            source_asset_root = source.local_path.parent
            content = normalize_file(input_path, source.title, source_asset_root)
            output_path = _build_output_path(output_root, source, input_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            source_hash = _sha256(input_path)
            markdown, document_images = _write_image_assets(
                content.markdown,
                content.images,
                source,
                output_path,
                output_root,
                repository_root,
                source_hash,
            )
            image_records.extend(document_images)
            image_ids = tuple(image.image_id for image in document_images)
            metadata = {
                "source_id": source.source_id,
                "tool": source.tool,
                "title": content.title,
                "source_url": _build_document_url(source, input_path),
                "source_path": input_path.relative_to(repository_root).as_posix(),
                "source_sha256": source_hash,
                "image_count": len(image_ids),
                "image_ids": list(image_ids),
            }
            output_path.write_text(_with_front_matter(metadata, markdown), encoding="utf-8")
            records.append(
                NormalizationRecord(
                    source_id=source.source_id,
                    input_path=metadata["source_path"],
                    output_path=output_path.relative_to(repository_root).as_posix(),
                    title=content.title,
                    image_count=len(image_ids),
                    image_ids=image_ids,
                    source_sha256=source_hash,
                )
            )

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "document_count": len(records),
        "image_reference_count": len(image_records),
        "documents": [asdict(record) for record in records],
    }
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "normalization-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    image_manifest = {
        "generated_at": report["generated_at"],
        "image_count": len(image_records),
        "available_count": sum(image.status == "available" for image in image_records),
        "external_count": sum(image.status == "external" for image in image_records),
        "missing_count": sum(image.status == "missing" for image in image_records),
        "images": [asdict(image) for image in image_records],
    }
    (output_root / "image-manifest.json").write_text(
        json.dumps(image_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return records


def _write_image_assets(
    markdown: str,
    images: tuple[ExtractedImage, ...],
    source: SourceSpec,
    output_path: Path,
    output_root: Path,
    repository_root: Path,
    source_hash: str,
) -> tuple[str, list[ImageManifestRecord]]:
    """写出图片内容、替换 Markdown 占位符，并生成图片清单记录。"""
    records: list[ImageManifestRecord] = []
    for image_number, image in enumerate(images, start=1):
        image_id = f"{source.source_id}-{source_hash[:10].lower()}-{image_number:04d}"
        asset_path: Path | None = None
        asset_hash: str | None = None
        if image.content is not None:
            extension = _image_extension(image.filename, image.media_type)
            asset_path = output_root / "assets" / source.source_id / f"{image_id}{extension}"
            asset_path.parent.mkdir(parents=True, exist_ok=True)
            asset_path.write_bytes(image.content)
            asset_hash = hashlib.sha256(image.content).hexdigest().upper()
            status = "available"
        elif image.original_uri and image.original_uri.startswith(("http://", "https://")):
            status = "external"
        else:
            status = "missing"

        caption = image.caption.replace("]", "\\]")
        markdown = markdown.replace(image.placeholder, f"![{caption}](asset://{image_id})")
        records.append(
            ImageManifestRecord(
                image_id=image_id,
                source_id=source.source_id,
                document_path=output_path.relative_to(repository_root).as_posix(),
                asset_path=asset_path.relative_to(repository_root).as_posix() if asset_path else None,
                original_uri=_portable_original_uri(image.original_uri, repository_root),
                caption=image.caption,
                media_type=image.media_type,
                extraction_method=image.extraction_method,
                page_number=image.page_number,
                section=image.section.split(":", maxsplit=1)[0] if image.section else None,
                width=image.width,
                height=image.height,
                sha256=asset_hash,
                status=status,
            )
        )
    return markdown, records


def _image_extension(filename: str, media_type: str) -> str:
    """从安全文件名或媒体类型推断标准图片扩展名。"""
    extension = Path(filename).suffix.lower()
    allowed_extensions = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".bmp", ".tif", ".tiff"}
    if extension in allowed_extensions:
        return extension
    guessed = mimetypes.guess_extension(media_type) or ".bin"
    return ".jpg" if guessed == ".jpe" else guessed


def _portable_original_uri(original_uri: str | None, repository_root: Path) -> str | None:
    """把项目内绝对路径转换为便于迁移的仓库相对路径。"""
    if not original_uri:
        return None
    candidate = Path(original_uri)
    if candidate.is_absolute():
        try:
            return candidate.relative_to(repository_root).as_posix()
        except ValueError:
            return candidate.name
    return original_uri


def _build_output_path(output_root: Path, source: SourceSpec, input_path: Path) -> Path:
    """按来源和原目录结构构造稳定的 Markdown 输出路径。"""
    if source.local_path.is_file():
        return output_root / source.source_id / f"{source.source_id}.md"
    relative_path = input_path.relative_to(source.local_path)
    return (output_root / source.source_id / relative_path).with_suffix(".md")


def _build_document_url(source: SourceSpec, input_path: Path) -> str:
    """为目录来源补上文件相对路径，形成可引用的原始文档地址。"""
    if source.local_path.is_file():
        return source.source_url
    relative_path = quote(input_path.relative_to(source.local_path).as_posix(), safe="/")
    source_url = source.source_url.replace("/tree/", "/blob/")
    return f"{source_url.rstrip('/')}/{relative_path}"


def _with_front_matter(metadata: dict[str, object], markdown: str) -> str:
    """在规范化正文前加入可供后续切分继承的来源元数据。"""
    front_matter = yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False).strip()
    return f"---\n{front_matter}\n---\n\n{markdown}"


def _sha256(path: Path) -> str:
    """流式计算文件的 SHA-256，避免一次读取大型文件。"""
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()

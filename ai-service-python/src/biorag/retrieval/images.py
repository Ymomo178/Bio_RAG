"""把文本块中的图片 ID 解析为可返回给前端的图片信息。"""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote


@dataclass(frozen=True)
class RetrievedImage:
    """表示一次检索结果中随正文返回的图片。"""

    image_id: str
    url: str | None
    caption: str
    source_id: str
    page_number: int | None
    section: str | None


def load_image_registry(manifest_path: Path) -> dict[str, dict[str, object]]:
    """读取图片清单并按 image_id 建立快速查询索引。"""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return {image["image_id"]: image for image in manifest.get("images", [])}


def resolve_chunk_images(
    markdown_chunk: str,
    registry: dict[str, dict[str, object]],
    public_base_url: str = "/api/rag/assets",
) -> list[RetrievedImage]:
    """解析文本块中的 asset URI，并组装去重后的图片返回结果。"""
    image_ids = list(dict.fromkeys(re.findall(r"asset://([A-Za-z0-9._-]+)", markdown_chunk)))
    results: list[RetrievedImage] = []
    for image_id in image_ids:
        record = registry.get(image_id)
        if not record:
            continue
        if record.get("status") == "available":
            url = f"{public_base_url.rstrip('/')}/{quote(image_id)}"
        elif record.get("status") == "external":
            url = str(record.get("original_uri"))
        else:
            url = None
        results.append(
            RetrievedImage(
                image_id=image_id,
                url=url,
                caption=str(record.get("caption") or ""),
                source_id=str(record.get("source_id") or ""),
                page_number=record.get("page_number"),
                section=record.get("section"),
            )
        )
    return results


def resolve_asset_file(
    image_id: str,
    registry: dict[str, dict[str, object]],
    repository_root: Path,
    asset_root: Path,
) -> Path | None:
    """在受控图片目录中定位资产文件，阻止路径穿越和任意文件读取。"""
    record = registry.get(image_id)
    if not record or record.get("status") != "available" or not record.get("asset_path"):
        return None
    candidate = (repository_root.resolve() / str(record["asset_path"])).resolve()
    try:
        candidate.relative_to(asset_root.resolve())
    except ValueError:
        return None
    return candidate if candidate.is_file() else None

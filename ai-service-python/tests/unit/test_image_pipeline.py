"""图片写出、清单和检索返回结果的端到端测试。"""

import base64
import json
from pathlib import Path

from biorag.ingestion.pipeline import normalize_manifest
from biorag.retrieval.images import load_image_registry, resolve_asset_file, resolve_chunk_images


def test_pipeline_writes_image_manifest_and_resolves_retrieval_image(tmp_path: Path) -> None:
    """规范化后的 asset URI 应能解析为前端可用的图片返回结构。"""
    data_directory = tmp_path / "data"
    raw_directory = data_directory / "raw"
    raw_directory.mkdir(parents=True)
    source = raw_directory / "tutorial.html"
    image_data = b"test-image-content"
    encoded_image = base64.b64encode(image_data).decode("ascii")
    source.write_text(
        f"<html><body><h1>教程</h1><h2>PCA</h2><img alt='PCA 图' src='data:image/png;base64,{encoded_image}'></body></html>",
        encoding="utf-8",
    )
    manifest_path = data_directory / "sources.yml"
    manifest_path.write_text(
        """
sources:
  - id: tutorial
    title: 教程
    tool: 测试工具
    source_type: html
    local_path: data/raw/tutorial.html
    source_url: https://example.org/tutorial.html
""",
        encoding="utf-8",
    )
    output_directory = data_directory / "normalized"

    records = normalize_manifest(manifest_path, output_directory)

    assert records[0].image_count == 1
    normalized_markdown = (output_directory / "tutorial" / "tutorial.md").read_text(encoding="utf-8")
    assert "asset://tutorial-" in normalized_markdown
    image_manifest_path = output_directory / "image-manifest.json"
    image_manifest = json.loads(image_manifest_path.read_text(encoding="utf-8"))
    assert image_manifest["available_count"] == 1
    image_record = image_manifest["images"][0]
    written_image = tmp_path / image_record["asset_path"]
    assert written_image.read_bytes() == image_data

    registry = load_image_registry(image_manifest_path)
    images = resolve_chunk_images(normalized_markdown, registry)
    assert len(images) == 1
    assert images[0].caption == "PCA 图"
    assert images[0].url == f"/api/rag/assets/{images[0].image_id}"
    resolved_file = resolve_asset_file(
        images[0].image_id,
        registry,
        tmp_path,
        output_directory / "assets",
    )
    assert resolved_file == written_image


def test_asset_file_rejects_path_outside_asset_root(tmp_path: Path) -> None:
    """图片文件定位器不得接受指向受控目录之外的清单路径。"""
    secret_file = tmp_path / "secret.txt"
    secret_file.write_text("secret", encoding="utf-8")
    registry = {
        "unsafe-image": {
            "status": "available",
            "asset_path": "secret.txt",
        }
    }

    resolved = resolve_asset_file(
        "unsafe-image",
        registry,
        tmp_path,
        tmp_path / "data" / "normalized" / "assets",
    )

    assert resolved is None

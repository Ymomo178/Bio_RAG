"""来源清单和白名单选择的单元测试。"""

from pathlib import Path

from biorag.ingestion.manifest import discover_source_files, load_sources


def test_manifest_selects_only_allowlisted_files(tmp_path: Path) -> None:
    """目录来源只能返回白名单文件，不能误选图片和开发文档。"""
    data_directory = tmp_path / "data"
    raw_directory = data_directory / "raw" / "example"
    raw_directory.mkdir(parents=True)
    (raw_directory / "useful.md").write_text("# 正文", encoding="utf-8")
    (raw_directory / "development.md").write_text("# 开发文档", encoding="utf-8")
    (raw_directory / "plot.png").write_bytes(b"image")
    manifest_path = data_directory / "sources.yml"
    manifest_path.write_text(
        """
sources:
  - id: example
    title: 示例
    tool: 示例工具
    source_type: markdown
    local_path: data/raw/example
    source_url: https://example.org/docs
    initial_index_include:
      - useful.md
""",
        encoding="utf-8",
    )

    source = load_sources(manifest_path)[0]
    selected = discover_source_files(source)

    assert selected == [(raw_directory / "useful.md").resolve()]

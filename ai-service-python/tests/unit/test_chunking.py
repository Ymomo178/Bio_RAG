"""结构化 Markdown 切分测试。"""

import json
from pathlib import Path

from biorag.ingestion.chunking import ChunkingConfig, chunk_markdown_document, chunk_normalized_directory


def _write_normalized_document(path: Path, body: str, source_path: str = "data/raw/guide.md") -> None:
    """写入测试使用的最小规范化 Markdown。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """---
source_id: test-guide
tool: TestTool
title: 测试指南
source_url: https://example.org/guide
source_path: SOURCE_PATH
source_sha256: ABC123
image_count: 1
image_ids:
  - test-image-0001
---

"""
        .replace("SOURCE_PATH", source_path)
        + body,
        encoding="utf-8",
    )


def test_chunk_inherits_section_page_and_image_metadata(tmp_path: Path) -> None:
    """文本块应继承章节、PDF 页码和正文实际引用的图片编号。"""
    normalized_root = tmp_path / "normalized"
    document_path = normalized_root / "test-guide" / "guide.md"
    _write_normalized_document(
        document_path,
        """# 测试指南

## 第 1 页

## 安装

第一段介绍安装要求。

![安装界面 [示例\\]](asset://test-image-0001)

## 第 2 页

第二页继续介绍运行方式。
""",
    )

    chunks = chunk_markdown_document(document_path, normalized_root, ChunkingConfig(max_chars=80, overlap_chars=10))

    assert {chunk.page_number for chunk in chunks} == {1, 2}
    image_chunk = next(chunk for chunk in chunks if chunk.image_ids)
    assert image_chunk.image_ids == ("test-image-0001",)
    assert image_chunk.section == "测试指南 > 安装"
    assert all(chunk.char_count <= 80 for chunk in chunks)
    assert all("测试指南" in chunk.embedding_text for chunk in chunks)


def test_hashes_inside_fenced_code_are_not_treated_as_headings(tmp_path: Path) -> None:
    """代码输出中的井号文本不能污染文档章节层级。"""
    normalized_root = tmp_path / "normalized"
    document_path = normalized_root / "test-guide" / "guide.md"
    _write_normalized_document(
        document_path,
        """# 使用方法

```text
## [1] TRUE
# 这也不是标题
```

代码块之后的说明。
""",
    )

    chunks = chunk_markdown_document(document_path, normalized_root)

    assert len(chunks) == 1
    assert chunks[0].section_path == ("使用方法",)
    assert "## [1] TRUE" in chunks[0].content


def test_pdf_code_comments_are_not_treated_as_markdown_headings(tmp_path: Path) -> None:
    """PDF 提取文本中的 R 注释不能被误认为文档标题。"""
    normalized_root = tmp_path / "normalized"
    document_path = normalized_root / "test-guide" / "guide.md"
    _write_normalized_document(
        document_path,
        """# 测试指南

## 第 1 页

Examples

# the raw counts
counts(dds)

# the FPM values
fpm(dds)
""",
        source_path="data/raw/guide.pdf",
    )

    chunks = chunk_markdown_document(document_path, normalized_root)

    assert len(chunks) == 1
    assert chunks[0].section_path == ("测试指南",)
    assert chunks[0].page_number == 1
    assert "# the raw counts" in chunks[0].content


def test_directory_chunking_writes_jsonl_and_report(tmp_path: Path) -> None:
    """目录任务应写出逐行 JSON 和可检查的统计报告。"""
    normalized_root = tmp_path / "normalized"
    document_path = normalized_root / "test-guide" / "guide.md"
    _write_normalized_document(document_path, "# 标题\n\n这是一段可检索正文。")
    output_path = tmp_path / "chunks" / "chunks.jsonl"

    report = chunk_normalized_directory(normalized_root, output_path)

    records = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]
    saved_report = json.loads((output_path.parent / "chunking-report.json").read_text(encoding="utf-8"))
    assert len(records) == 1
    assert records[0]["source_id"] == "test-guide"
    assert report["document_count"] == 1
    assert saved_report["chunk_count"] == 1


def test_oversized_table_header_respects_chunk_limit(tmp_path: Path) -> None:
    """表头自身超长时不能因重复表头而突破文本块长度限制。"""
    normalized_root = tmp_path / "normalized"
    document_path = normalized_root / "test-guide" / "guide.md"
    long_cell = "A" * 120
    _write_normalized_document(
        document_path,
        f"# 表格\n\n| 名称 | {long_cell} |\n| --- | --- |\n| 示例 | 内容 |",
    )

    chunks = chunk_markdown_document(
        document_path,
        normalized_root,
        ChunkingConfig(max_chars=80, overlap_chars=10),
    )

    assert chunks
    assert all(chunk.char_count <= 80 for chunk in chunks)

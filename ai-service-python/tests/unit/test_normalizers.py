"""文档格式规范化器的单元测试。"""

from pathlib import Path

import pymupdf
from pypdf import PdfWriter

from biorag.ingestion.normalizers import _rows_to_markdown, normalize_file


def test_html_removes_scripts_and_embedded_image_data(tmp_path: Path) -> None:
    """HTML 转换应移除脚本和 Base64，只保留图片说明。"""
    source = tmp_path / "tutorial.html"
    source.write_text(
        """
        <html><head><title>教程</title><script>bad()</script></head>
        <body><nav>导航噪声</nav><h1>DESeq2 教程</h1>
        <p>有效正文</p><img alt="MA 图" src="data:image/png;base64,AAAA" /></body></html>
        """,
        encoding="utf-8",
    )

    result = normalize_file(source, "备用标题")

    assert result.title == "DESeq2 教程"
    assert result.image_count == 1
    assert "有效正文" in result.markdown
    assert result.images[0].caption == "MA 图"
    assert result.images[0].content == b"\x00\x00\x00"
    assert result.images[0].placeholder in result.markdown
    assert "导航噪声" not in result.markdown
    assert "base64" not in result.markdown
    assert "bad()" not in result.markdown


def test_mdx_removes_front_matter_imports_and_components(tmp_path: Path) -> None:
    """MDX 转换应保留正文，同时清除页面配置和组件标签。"""
    source = tmp_path / "guide.mdx"
    source.write_text(
        """---
title: "Salmon 指南"
---
import Aside from '@theme/Aside';
<Aside type="note">
需要保留的提示
</Aside>
""",
        encoding="utf-8",
    )

    result = normalize_file(source, "备用标题")

    assert result.title == "Salmon 指南"
    assert "需要保留的提示" in result.markdown
    assert "import Aside" not in result.markdown
    assert "<Aside" not in result.markdown


def test_rst_converts_sphinx_references_to_readable_text(tmp_path: Path) -> None:
    """RST 转换应清除 Sphinx 角色，但不能丢失链接标签文字。"""
    source = tmp_path / "guide.rst"
    source.write_text(
        """用户指南
========

请查看 :ref:`过滤选项 <filtering>` 和 :option:`--minimum-length`。
""",
        encoding="utf-8",
    )

    result = normalize_file(source, "备用标题")

    assert result.title == "用户指南"
    assert "过滤选项" in result.markdown
    assert "--minimum-length" in result.markdown
    assert ":ref:" not in result.markdown
    assert ":option:" not in result.markdown


def test_pdf_keeps_page_boundaries(tmp_path: Path) -> None:
    """PDF 转换即使遇到空白页，也应保留明确的页码边界。"""
    source = tmp_path / "manual.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    with source.open("wb") as output:
        writer.write(output)

    result = normalize_file(source, "测试手册")

    assert result.title == "测试手册"
    assert "## 第 1 页" in result.markdown
    assert "[本页没有可提取文本]" in result.markdown


def test_pdf_extracts_embedded_image_and_page_number(tmp_path: Path) -> None:
    """PDF 转换应提取原始图片，并记录图片所在页码。"""
    source = tmp_path / "illustrated.pdf"
    image_data = b"P6\n2 2\n255\n" + bytes([255, 0, 0, 0, 255, 0, 0, 0, 255, 255, 255, 0])
    document = pymupdf.open()
    page = document.new_page(width=300, height=300)
    page.insert_text((40, 30), "Figure 1")
    page.insert_image(pymupdf.Rect(50, 50, 250, 250), stream=image_data)
    document.save(source)
    document.close()

    result = normalize_file(source, "带图手册")

    assert result.image_count == 1
    assert result.images[0].content
    assert result.images[0].page_number == 1
    assert result.images[0].placeholder in result.markdown


def test_table_rows_convert_to_markdown() -> None:
    """结构化表格行应转换成包含表头和分隔行的 Markdown。"""
    markdown = _rows_to_markdown([["样本", "计数"], ["A", "12"], ["B", "18"]])

    assert "| 样本 | 计数 |" in markdown
    assert "| --- | --- |" in markdown
    assert "| A | 12 |" in markdown

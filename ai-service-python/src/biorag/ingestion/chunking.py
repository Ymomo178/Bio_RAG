"""把规范化 Markdown 切分为可检索、可追溯的文本块。"""

import hashlib
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml


_FRONT_MATTER_PATTERN = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", re.DOTALL)
_HEADING_PATTERN = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t]*#*[ \t]*$")
_PAGE_PATTERN = re.compile(r"^第\s*(\d+)\s*页$")
_FENCE_PATTERN = re.compile(r"^\s*(`{3,}|~{3,})")
_IMAGE_PATTERN = re.compile(r"!\[(?:\\.|[^\]])*]\(asset://([^)\s]+)\)")
_TABLE_SEPARATOR_PATTERN = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$")


@dataclass(frozen=True)
class ChunkingConfig:
    """保存文本块大小和相邻文本重叠量。"""

    max_chars: int = 1200
    overlap_chars: int = 150

    def __post_init__(self) -> None:
        """拒绝会产生空块或无限重叠的无效参数。"""
        if self.max_chars <= 0:
            raise ValueError("max_chars 必须大于 0")
        if self.overlap_chars < 0:
            raise ValueError("overlap_chars 不能小于 0")
        if self.overlap_chars >= self.max_chars:
            raise ValueError("overlap_chars 必须小于 max_chars")


@dataclass(frozen=True)
class DocumentChunk:
    """表示一个即将用于 Embedding 和检索的文本块。"""

    chunk_id: str
    chunk_index: int
    source_id: str
    tool: str
    document_title: str
    source_url: str
    source_path: str
    normalized_path: str
    source_sha256: str
    section_path: tuple[str, ...]
    section: str | None
    page_number: int | None
    image_ids: tuple[str, ...]
    content: str
    embedding_text: str
    char_count: int


@dataclass(frozen=True)
class _DocumentSegment:
    """保存同一章节和同一 PDF 页内尚未按长度切分的正文。"""

    section_path: tuple[str, ...]
    page_number: int | None
    content: str


def chunk_markdown_document(
    document_path: Path,
    input_root: Path,
    config: ChunkingConfig | None = None,
) -> list[DocumentChunk]:
    """读取一份规范化 Markdown，并返回带完整来源信息的文本块。"""
    config = config or ChunkingConfig()
    document_path = document_path.resolve()
    input_root = input_root.resolve()
    metadata, markdown = _read_normalized_document(document_path)
    normalized_path = document_path.relative_to(input_root).as_posix()
    chunks: list[DocumentChunk] = []

    source_path = str(metadata.get("source_path", ""))
    parse_structural_headings = Path(source_path).suffix.lower() != ".pdf"
    for segment in _split_into_segments(
        markdown,
        parse_structural_headings=parse_structural_headings,
        document_title=str(metadata.get("title", document_path.stem)),
    ):
        blocks = _split_markdown_blocks(segment.content, config.max_chars)
        for content in _pack_blocks(blocks, config):
            chunk_index = len(chunks)
            section = " > ".join(segment.section_path) or None
            image_ids = _extract_image_ids(content)
            chunk_id = _build_chunk_id(
                str(metadata.get("source_id", "unknown")),
                normalized_path,
                chunk_index,
                content,
            )
            chunks.append(
                DocumentChunk(
                    chunk_id=chunk_id,
                    chunk_index=chunk_index,
                    source_id=str(metadata.get("source_id", "")),
                    tool=str(metadata.get("tool", "")),
                    document_title=str(metadata.get("title", document_path.stem)),
                    source_url=str(metadata.get("source_url", "")),
                    source_path=str(metadata.get("source_path", "")),
                    normalized_path=normalized_path,
                    source_sha256=str(metadata.get("source_sha256", "")),
                    section_path=segment.section_path,
                    section=section,
                    page_number=segment.page_number,
                    image_ids=image_ids,
                    content=content,
                    embedding_text=_build_embedding_text(metadata, section, segment.page_number, content),
                    char_count=len(content),
                )
            )
    return chunks


def chunk_normalized_directory(
    input_root: Path,
    output_path: Path,
    config: ChunkingConfig | None = None,
) -> dict[str, Any]:
    """切分目录中的全部 Markdown，并写出 JSONL 和质量统计报告。"""
    config = config or ChunkingConfig()
    input_root = input_root.resolve()
    output_path = output_path.resolve()
    document_paths = sorted(path for path in input_root.rglob("*.md") if path.is_file())
    if not document_paths:
        raise ValueError(f"没有在目录中找到 Markdown：{input_root}")

    all_chunks: list[DocumentChunk] = []
    document_chunk_counts: dict[str, int] = {}
    for document_path in document_paths:
        document_chunks = chunk_markdown_document(document_path, input_root, config)
        relative_path = document_path.relative_to(input_root).as_posix()
        document_chunk_counts[relative_path] = len(document_chunks)
        all_chunks.extend(document_chunks)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(f"{output_path.suffix}.tmp")
    with temporary_path.open("w", encoding="utf-8", newline="\n") as output_file:
        for chunk in all_chunks:
            output_file.write(json.dumps(asdict(chunk), ensure_ascii=False) + "\n")
    temporary_path.replace(output_path)

    char_counts = [chunk.char_count for chunk in all_chunks]
    source_counts = Counter(chunk.source_id for chunk in all_chunks)
    report = {
        "document_count": len(document_paths),
        "chunk_count": len(all_chunks),
        "chunks_with_images": sum(bool(chunk.image_ids) for chunk in all_chunks),
        "chunks_with_page_number": sum(chunk.page_number is not None for chunk in all_chunks),
        "min_chunk_chars": min(char_counts, default=0),
        "max_chunk_chars": max(char_counts, default=0),
        "average_chunk_chars": round(sum(char_counts) / len(char_counts), 2) if char_counts else 0,
        "max_chars": config.max_chars,
        "overlap_chars": config.overlap_chars,
        "source_chunk_counts": dict(sorted(source_counts.items())),
        "document_chunk_counts": document_chunk_counts,
    }
    report_path = output_path.with_name("chunking-report.json")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def _read_normalized_document(document_path: Path) -> tuple[dict[str, Any], str]:
    """分离 Markdown 顶部的 YAML 元数据和正文。"""
    text = document_path.read_text(encoding="utf-8-sig")
    match = _FRONT_MATTER_PATTERN.match(text)
    if match is None:
        raise ValueError(f"规范化文档缺少 YAML 元数据：{document_path}")
    metadata = yaml.safe_load(match.group(1)) or {}
    if not isinstance(metadata, dict):
        raise ValueError(f"YAML 元数据必须是对象：{document_path}")
    return metadata, text[match.end() :].strip()


def _split_into_segments(
    markdown: str,
    parse_structural_headings: bool,
    document_title: str,
) -> list[_DocumentSegment]:
    """按标题和 PDF 页码切分正文，同时忽略代码块内部的井号。"""
    lines = markdown.splitlines()
    headings: list[tuple[int, str]] = []
    page_number: int | None = None
    current_lines: list[str] = []
    segments: list[_DocumentSegment] = []
    active_fence: str | None = None

    def flush() -> None:
        """把当前缓冲区写成一个结构段。"""
        content = "\n".join(current_lines).strip()
        if content:
            segments.append(
                _DocumentSegment(
                    section_path=tuple(title for _, title in headings),
                    page_number=page_number,
                    content=content,
                )
            )
        current_lines.clear()

    for line_number, line in enumerate(lines):
        fence_match = _FENCE_PATTERN.match(line)
        if active_fence is not None:
            current_lines.append(line)
            if fence_match and fence_match.group(1)[0] == active_fence:
                active_fence = None
            continue
        if fence_match:
            active_fence = fence_match.group(1)[0]
            current_lines.append(line)
            continue

        heading_match = _HEADING_PATTERN.match(line)
        if heading_match:
            level = len(heading_match.group(1))
            title = heading_match.group(2).strip()
            page_match = _PAGE_PATTERN.fullmatch(title)
            if page_match:
                flush()
                page_number = int(page_match.group(1))
                continue
            if parse_structural_headings:
                flush()
                headings = [(old_level, old_title) for old_level, old_title in headings if old_level < level]
                headings.append((level, title))
                continue
            if line_number == 0 and level == 1 and title == document_title:
                headings = [(1, title)]
                continue
        current_lines.append(line)

    flush()
    return segments


def _split_markdown_blocks(content: str, max_chars: int) -> list[str]:
    """按空行和围栏代码块形成语义块，再拆开超长语义块。"""
    blocks: list[str] = []
    current_lines: list[str] = []
    active_fence: str | None = None

    def flush() -> None:
        """写出缓冲区，并确保任何单块都不超过长度上限。"""
        block = "\n".join(current_lines).strip()
        if block:
            blocks.extend(_split_oversized_block(block, max_chars))
        current_lines.clear()

    for line in content.splitlines():
        fence_match = _FENCE_PATTERN.match(line)
        if active_fence is not None:
            current_lines.append(line)
            if fence_match and fence_match.group(1)[0] == active_fence:
                active_fence = None
                flush()
            continue
        if fence_match:
            flush()
            active_fence = fence_match.group(1)[0]
            current_lines.append(line)
            continue
        if not line.strip():
            flush()
            continue
        current_lines.append(line)
    flush()
    return blocks


def _split_oversized_block(block: str, max_chars: int) -> list[str]:
    """拆分超长段落，并尽量保持代码围栏和表头完整。"""
    if len(block) <= max_chars:
        return [block]
    lines = block.splitlines()
    if len(lines) >= 2 and _FENCE_PATTERN.match(lines[0]):
        opener = lines[0]
        closer = lines[-1] if _FENCE_PATTERN.match(lines[-1]) else opener[:3]
        body = "\n".join(lines[1:-1] if lines[-1] == closer else lines[1:])
        available_chars = max(1, max_chars - len(opener) - len(closer) - 2)
        return [f"{opener}\n{part}\n{closer}" for part in _split_plain_text(body, available_chars)]
    if len(lines) >= 2 and "|" in lines[0] and _TABLE_SEPARATOR_PATTERN.match(lines[1]):
        header = "\n".join(lines[:2])
        if len(header) + 1 >= max_chars:
            return _split_plain_text(block, max_chars)
        available_chars = max(1, max_chars - len(header) - 1)
        body_parts = _split_plain_text("\n".join(lines[2:]), available_chars)
        return [f"{header}\n{part}" for part in body_parts]
    return _split_plain_text(block, max_chars)


def _split_plain_text(text: str, max_chars: int) -> list[str]:
    """优先按行和句子拆分普通文本，最后才按字符硬切。"""
    units: list[str] = []
    for line in text.splitlines() or [text]:
        if len(line) <= max_chars:
            units.append(line)
            continue
        sentences = re.split(r"(?<=[。！？.!?])\s+", line)
        for sentence in sentences:
            if len(sentence) <= max_chars:
                units.append(sentence)
            else:
                units.extend(sentence[start : start + max_chars] for start in range(0, len(sentence), max_chars))

    parts: list[str] = []
    current: list[str] = []
    for unit in units:
        separator = "\n" if current else ""
        if current and len(separator.join(current + [unit])) > max_chars:
            parts.append("\n".join(current).strip())
            current = [unit]
        else:
            current.append(unit)
    if current:
        parts.append("\n".join(current).strip())
    return [part for part in parts if part]


def _pack_blocks(blocks: list[str], config: ChunkingConfig) -> list[str]:
    """把语义块装入定长文本块，并从上一块携带少量完整段落。"""
    packed: list[str] = []
    current: list[str] = []
    for block in blocks:
        if not current:
            current = [block]
            continue
        candidate = "\n\n".join(current + [block])
        if len(candidate) <= config.max_chars:
            current.append(block)
            continue

        packed.append("\n\n".join(current))
        carry = _select_overlap_blocks(current, config.overlap_chars)
        while carry and len("\n\n".join(carry + [block])) > config.max_chars:
            carry.pop(0)
        current = carry + [block]
    if current:
        packed.append("\n\n".join(current))
    return packed


def _select_overlap_blocks(blocks: list[str], overlap_chars: int) -> list[str]:
    """从上一块末尾选择不超过重叠预算的完整语义段。"""
    if overlap_chars == 0:
        return []
    selected: list[str] = []
    current_length = 0
    for block in reversed(blocks):
        added_length = len(block) + (2 if selected else 0)
        if current_length + added_length > overlap_chars:
            break
        selected.insert(0, block)
        current_length += added_length
    return selected


def _extract_image_ids(content: str) -> tuple[str, ...]:
    """按正文出现顺序提取并去重 asset 图片编号。"""
    return tuple(dict.fromkeys(_IMAGE_PATTERN.findall(content)))


def _build_embedding_text(
    metadata: dict[str, Any],
    section: str | None,
    page_number: int | None,
    content: str,
) -> str:
    """把文档和章节上下文加入正文，形成后续向量化的实际输入。"""
    context = [str(metadata.get("title", ""))]
    if section:
        context.append(section)
    if page_number is not None:
        context.append(f"第 {page_number} 页")
    context.append(content)
    return "\n\n".join(item for item in context if item)


def _build_chunk_id(source_id: str, normalized_path: str, chunk_index: int, content: str) -> str:
    """根据来源、文件、顺序和正文生成可重复计算的稳定编号。"""
    identity = f"{normalized_path}\n{chunk_index}\n{content}".encode("utf-8")
    digest = hashlib.sha256(identity).hexdigest()[:16]
    return f"{source_id}-{digest}"

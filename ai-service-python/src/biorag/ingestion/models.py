"""文档规范化流程使用的数据模型。"""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SourceSpec:
    """描述一个知识来源及其首版索引白名单。"""

    source_id: str
    title: str
    tool: str
    source_type: str
    local_path: Path
    source_url: str
    include_patterns: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExtractedImage:
    """保存从源文档提取或引用的一张图片。"""

    placeholder: str
    filename: str
    media_type: str
    content: bytes | None
    caption: str
    extraction_method: str
    original_uri: str | None = None
    page_number: int | None = None
    section: str | None = None
    width: int | None = None
    height: int | None = None


@dataclass(frozen=True)
class NormalizedContent:
    """保存单个文件规范化后的正文和图片资产。"""

    title: str
    markdown: str
    images: tuple[ExtractedImage, ...] = ()

    @property
    def image_count(self) -> int:
        """返回正文关联的图片数量。"""
        return len(self.images)


@dataclass(frozen=True)
class NormalizationRecord:
    """记录一个原始文件的规范化结果。"""

    source_id: str
    input_path: str
    output_path: str
    title: str
    image_count: int
    image_ids: tuple[str, ...]
    source_sha256: str


@dataclass(frozen=True)
class ImageManifestRecord:
    """记录可供检索结果返回的一张标准化图片。"""

    image_id: str
    source_id: str
    document_path: str
    asset_path: str | None
    original_uri: str | None
    caption: str
    media_type: str
    extraction_method: str
    page_number: int | None
    section: str | None
    width: int | None
    height: int | None
    sha256: str | None
    status: str

"""读取来源清单并按照白名单选择文件。"""

from pathlib import Path

import yaml

from biorag.ingestion.models import SourceSpec


def load_sources(manifest_path: Path) -> list[SourceSpec]:
    """读取 sources.yml，并把相对路径解析为项目内的绝对路径。"""
    manifest_path = manifest_path.resolve()
    repository_root = manifest_path.parent.parent
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))

    sources: list[SourceSpec] = []
    for item in manifest.get("sources", []):
        sources.append(
            SourceSpec(
                source_id=item["id"],
                title=item["title"],
                tool=item["tool"],
                source_type=item["source_type"],
                local_path=(repository_root / item["local_path"]).resolve(),
                source_url=item["source_url"],
                include_patterns=tuple(item.get("initial_index_include", [])),
            )
        )
    return sources


def discover_source_files(source: SourceSpec) -> list[Path]:
    """根据来源类型和白名单返回允许进入首版索引的文件。"""
    if source.local_path.is_file():
        return [source.local_path]
    if not source.local_path.is_dir():
        raise FileNotFoundError(f"来源路径不存在：{source.local_path}")
    if not source.include_patterns:
        raise ValueError(f"目录来源缺少 initial_index_include：{source.source_id}")

    selected: set[Path] = set()
    for pattern in source.include_patterns:
        selected.update(path.resolve() for path in source.local_path.glob(pattern) if path.is_file())

    missing_patterns = [
        pattern
        for pattern in source.include_patterns
        if not any(path.is_file() for path in source.local_path.glob(pattern))
    ]
    if missing_patterns:
        missing_text = ", ".join(missing_patterns)
        raise FileNotFoundError(f"{source.source_id} 的白名单没有匹配文件：{missing_text}")
    return sorted(selected)


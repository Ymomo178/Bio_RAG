"""评测集隔离命令的最小测试。"""

import json
from pathlib import Path

from biorag.evaluation.isolation_cli import main


def _write(path: Path, records: list[dict[str, object]]) -> None:
    """写入测试用 JSONL。"""
    path.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in records), encoding="utf-8")


def test_isolation_cli_writes_report(tmp_path: Path, monkeypatch) -> None:
    """隔离命令应写出 isolated=true 报告。"""
    chunks = tmp_path / "chunks.jsonl"
    development = tmp_path / "development.jsonl"
    test = tmp_path / "test.jsonl"
    output = tmp_path / "report.json"
    _write(
        chunks,
        [
            {"chunk_id": "dev-chunk", "source_id": "guide", "normalized_path": "guide.md", "content": "开发答案"},
            {"chunk_id": "test-chunk", "source_id": "guide", "normalized_path": "guide.md", "content": "测试答案"},
        ],
    )
    base = {
        "expected_answer": "答案",
        "source_id": "guide",
        "normalized_path": "guide.md",
        "expected_section": "section",
        "page_number": None,
        "category": "test",
        "difficulty": "easy",
    }
    _write(development, [{**base, "question_id": "dev-1", "question": "开发问题", "evidence_quote": "开发答案"}])
    _write(test, [{**base, "question_id": "test-1", "question": "测试问题", "evidence_quote": "测试答案"}])
    monkeypatch.setattr(
        "sys.argv",
        [
            "biorag-eval-isolation",
            "--development",
            str(development),
            "--test",
            str(test),
            "--chunks",
            str(chunks),
            "--output",
            str(output),
        ],
    )

    main()

    assert json.loads(output.read_text(encoding="utf-8"))["isolated"] is True

"""加载项目根目录的本地环境变量。"""

from pathlib import Path


def load_project_environment() -> Path | None:
    """从常见项目位置读取 .env，且不覆盖操作系统已设置的变量。"""
    try:
        from dotenv import load_dotenv
    except ImportError as error:
        raise RuntimeError("请安装服务依赖：pip install -e '.[service]'") from error

    candidates = (
        Path.cwd() / ".env",
        Path.cwd().parent / ".env",
        Path(__file__).resolve().parents[3] / ".env",
    )
    for candidate in dict.fromkeys(path.resolve() for path in candidates):
        if candidate.is_file():
            load_dotenv(candidate, override=False)
            return candidate
    return None

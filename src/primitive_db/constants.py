from __future__ import annotations

from pathlib import Path

APP_NAME = "Primitive DB"

# Runtime artifacts (must be ignored in git)
META_FILENAME = "db_meta.json"
DATA_DIRNAME = "data"
LOG_DIRNAME = "logs"
LOG_FILENAME = "commands.log"

SUPPORTED_TYPES: dict[str, type] = {
    "int": int,
    "float": float,
    "str": str,
    "bool": bool,
}

BOOL_TRUE = {"true", "1", "yes", "y", "да", "д"}
BOOL_FALSE = {"false", "0", "no", "n", "нет", "н"}


def default_db_root() -> Path:
    """Возвращает директорию, относительно которой будут храниться данные БД.
"""
    # База живёт относительно текущей директории запуска.
    return Path.cwd()


def meta_path(db_root: Path) -> Path:
    """Путь к файлу метаданных (db_meta.json).
"""
    return db_root / META_FILENAME


def data_dir(db_root: Path) -> Path:
    """Путь к директории с таблицами (data/).
"""
    return db_root / DATA_DIRNAME


def log_dir(db_root: Path) -> Path:
    """Путь к директории логов (logs/).
"""
    return db_root / LOG_DIRNAME


def log_path(db_root: Path) -> Path:
    """Путь к файлу логов команд (logs/commands.log).
"""
    return log_dir(db_root) / LOG_FILENAME

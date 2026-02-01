from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .constants import data_dir, meta_path
from .errors import StorageError


def _read_json(path: Path, *, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise StorageError(f"Не удалось прочитать JSON: {path}") from exc


def _write_json_atomic(path: Path, payload: Any) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        tmp.replace(path)
    except OSError as exc:
        raise StorageError(f"Не удалось записать JSON: {path}") from exc


def load_meta(db_root: Path) -> dict[str, Any]:
    """Читает метаданные БД (список таблиц и схем) из db_meta.json.
"""
    return _read_json(meta_path(db_root), default={"tables": {}})


def save_meta(db_root: Path, meta: dict[str, Any]) -> None:
    """Сохраняет метаданные БД в db_meta.json атомарно.
"""
    _write_json_atomic(meta_path(db_root), meta)


def table_path(db_root: Path, table: str) -> Path:
    """Возвращает путь к файлу таблицы <table>.json в директории data/.
"""
    return data_dir(db_root) / f"{table}.json"


def load_table(db_root: Path, table: str) -> list[dict[str, Any]]:
    """Читает строки таблицы из JSON-файла и возвращает список словарей.
"""
    return _read_json(table_path(db_root, table), default=[])


def save_table(db_root: Path, table: str, rows: list[dict[str, Any]]) -> None:
    """Сохраняет строки таблицы в JSON-файл атомарно.
"""
    _write_json_atomic(table_path(db_root, table), rows)


def ensure_data_dir(db_root: Path) -> None:
    """Гарантирует существование директории data/.
"""
    try:
        data_dir(db_root).mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise StorageError(f"Не удалось создать директорию данных: {data_dir(db_root)}") from exc

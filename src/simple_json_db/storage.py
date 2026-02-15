from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class StorageError(RuntimeError):
    """Ошибки доступа к файлам базы данных."""


@dataclass
class StoragePaths:
    root: Path
    meta: Path
    data_dir: Path

    @staticmethod
    def for_project(root_dir: Path) -> "StoragePaths":
        db_root = root_dir / "db"
        return StoragePaths(
            root=db_root,
            meta=db_root / "meta.json",
            data_dir=db_root,
        )


def ensure_dirs(paths: StoragePaths) -> None:
    paths.root.mkdir(parents=True, exist_ok=True)
    paths.data_dir.mkdir(parents=True, exist_ok=True)


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise StorageError(f"Не удалось прочитать {path}: {exc}") from exc


def write_json(path: Path, data: Any) -> None:
    try:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        raise StorageError(f"Не удалось записать {path}: {exc}") from exc


def table_path(paths: StoragePaths, table: str) -> Path:
    return paths.data_dir / f"{table}.json"

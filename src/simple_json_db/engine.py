from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .schema import SchemaError, TableSchema
from .storage import StoragePaths, ensure_dirs, read_json, table_path, write_json
from .where import compile_where


class EngineError(RuntimeError):
    """Ошибки выполнения команд."""


@dataclass
class DBEngine:
    root_dir: Path
    paths: StoragePaths

    @staticmethod
    def open(root_dir: Path) -> "DBEngine":
        paths = StoragePaths.for_project(root_dir)
        ensure_dirs(paths)
        engine = DBEngine(root_dir=root_dir, paths=paths)
        engine._init_meta()
        return engine

    def _init_meta(self) -> None:
        meta = read_json(self.paths.meta, default={"tables": {}, "counters": {}})
        if "tables" not in meta or "counters" not in meta:
            meta = {"tables": {}, "counters": {}}
        write_json(self.paths.meta, meta)

    def _meta(self) -> dict[str, Any]:
        return read_json(self.paths.meta, default={"tables": {}, "counters": {}})

    def _save_meta(self, meta: dict[str, Any]) -> None:
        write_json(self.paths.meta, meta)

    def list_tables(self) -> dict[str, dict[str, str]]:
        meta = self._meta()
        return meta["tables"]

    def create_table(self, name: str, schema_parts: list[str]) -> None:
        meta = self._meta()
        if name in meta["tables"]:
            raise EngineError(f"Таблица {name!r} уже существует")
        fields = TableSchema.parse_schema_parts(schema_parts)
        meta["tables"][name] = fields
        meta["counters"][name] = 0
        self._save_meta(meta)
        write_json(table_path(self.paths, name), [])
        return None

    def drop_table(self, name: str) -> None:
        meta = self._meta()
        if name not in meta["tables"]:
            raise EngineError(f"Таблица {name!r} не найдена")
        meta["tables"].pop(name, None)
        meta["counters"].pop(name, None)
        self._save_meta(meta)
        tp = table_path(self.paths, name)
        if tp.exists():
            tp.unlink()
        return None

    def insert(self, table: str, raw_pairs: dict[str, str]) -> dict[str, Any]:
        schema = self._schema(table)
        meta = self._meta()
        payload = schema.validate_insert(raw_pairs)

        meta["counters"][table] += 1
        row_id = meta["counters"][table]
        payload["id"] = row_id

        rows = read_json(table_path(self.paths, table), default=[])
        rows.append(payload)
        write_json(table_path(self.paths, table), rows)
        self._save_meta(meta)
        return payload

    def select(self, table: str, where: str | None) -> list[dict[str, Any]]:
        self._schema(table)  # проверить наличие
        rows = read_json(table_path(self.paths, table), default=[])
        if where:
            pred = compile_where(where).fn
            return [r for r in rows if pred(r)]
        return rows

    def update(self, table: str, set_pairs: dict[str, str], where: str | None) -> int:
        schema = self._schema(table)
        cooked = schema.validate_update(set_pairs)

        rows = read_json(table_path(self.paths, table), default=[])
        pred = compile_where(where or "").fn
        changed = 0
        for row in rows:
            if pred(row):
                row.update(cooked)
                changed += 1
        write_json(table_path(self.paths, table), rows)
        return changed

    def delete(self, table: str, where: str | None) -> int:
        self._schema(table)
        rows = read_json(table_path(self.paths, table), default=[])
        if where:
            pred = compile_where(where).fn
            keep = [r for r in rows if not pred(r)]
            deleted = len(rows) - len(keep)
            write_json(table_path(self.paths, table), keep)
            return deleted
        # без where удаляем всё
        deleted = len(rows)
        write_json(table_path(self.paths, table), [])
        return deleted

    def _schema(self, table: str) -> TableSchema:
        meta = self._meta()
        if table not in meta["tables"]:
            raise EngineError(f"Таблица {table!r} не найдена")
        return TableSchema(name=table, fields=meta["tables"][table])

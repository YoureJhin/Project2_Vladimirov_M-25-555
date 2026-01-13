from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional

from .constants import SUPPORTED_TYPES, default_db_root
from .decorators import confirm_action, handle_db_errors, log_command, log_time
from .errors import SchemaError, TableExistsError, TableNotFoundError, ValidationError
from .storage import ensure_data_dir, load_meta, load_table, save_meta, save_table, table_path
from .utils import Condition, ensure_identifier, parse_scalar


@dataclass(frozen=True)
class SelectResult:
    """Результат команды select: строки и признак попадания в кэш.
"""
    rows: list[dict[str, Any]]
    from_cache: bool


def _make_select_cache():
    cache: dict[tuple[str, str, int], list[dict[str, Any]]] = {}

    def cached(
        table: str,
        where_key: str,
        version: int,
        compute: Callable[[], list[dict[str, Any]]],
    ) -> SelectResult:
        key = (table, where_key, version)
        if key in cache:
            # defensive copy
            return SelectResult(rows=[dict(r) for r in cache[key]], from_cache=True)
        rows = compute()
        cache[key] = [dict(r) for r in rows]
        return SelectResult(rows=rows, from_cache=False)

    return cached


class PrimitiveDB:
    """Файловая база данных: управление таблицами и CRUD через JSON-хранилище.
"""
    def __init__(self, db_root: Optional[Path] = None):
        self.db_root = db_root or default_db_root()
        ensure_data_dir(self.db_root)
        self._meta = load_meta(self.db_root)
        self._versions: dict[str, int] = {t: 0 for t in self._meta.get("tables", {}).keys()}
        self._select_cached = _make_select_cache()

    def _touch(self, table: str) -> None:
        self._versions[table] = self._versions.get(table, 0) + 1

    def _get_table(self, table: str) -> dict[str, Any]:
        tables = self._meta.get("tables", {})
        if table not in tables:
            raise TableNotFoundError(f"Таблица не найдена: {table!r}")
        return tables[table]

    def _save_meta(self) -> None:
        save_meta(self.db_root, self._meta)

    @handle_db_errors
    @log_time
    @log_command
    def list_tables(self) -> list[dict[str, Any]]:
        tables = self._meta.get("tables", {})
        result: list[dict[str, Any]] = []
        for name, info in sorted(tables.items(), key=lambda x: x[0]):
            result.append(
                {
                    "table": name,
                    "schema": dict(info.get("schema", {})),
                    "rows_file": str(table_path(self.db_root, name)),
                }
            )
        return result

    @handle_db_errors
    @log_time
    @log_command
    def create_table(self, table: str, columns: list[tuple[str, str]]) -> None:
        ensure_identifier(table, what="таблицы")
        if table in self._meta.get("tables", {}):
            raise TableExistsError(f"Таблица уже существует: {table!r}")
        if not columns:
            raise SchemaError("Нельзя создать таблицу без полей")

        schema: dict[str, str] = {}
        for field, type_name in columns:
            if field == "id":
                raise SchemaError("Поле 'id' зарезервировано (генерируется автоматически)")
            if field in schema:
                raise SchemaError(f"Дублирующееся поле: {field!r}")
            if type_name not in SUPPORTED_TYPES:
                raise SchemaError(f"Неподдерживаемый тип: {type_name!r}")
            schema[field] = type_name

        self._meta.setdefault("tables", {})[table] = {"schema": schema, "last_id": 0}
        self._save_meta()
        save_table(self.db_root, table, [])
        self._versions[table] = 0
        print(f"OK: таблица {table!r} создана.")

    @handle_db_errors
    @log_time
    @log_command
    @confirm_action("Удалить таблицу?")
    def drop_table(self, table: str) -> None:
        ensure_identifier(table, what="таблицы")
        tables = self._meta.get("tables", {})
        if table not in tables:
            raise TableNotFoundError(f"Таблица не найдена: {table!r}")
        # remove file
        path = table_path(self.db_root, table)
        if path.exists():
            path.unlink()
        del tables[table]
        self._save_meta()
        self._versions.pop(table, None)
        print(f"OK: таблица {table!r} удалена.")

    def _coerce_where(self, table: str, where: Optional[list[Condition]]) -> list[tuple[str, str, Any]]:
        if not where:
            return []

        table_info = self._get_table(table)
        schema: dict[str, str] = table_info.get("schema", {})
        prepared: list[tuple[str, str, Any]] = []
        for cond in where:
            field = cond.field
            op = cond.op
            if field == "id":
                type_name = "int"
            else:
                if field not in schema:
                    raise ValidationError(f"Неизвестное поле в where: {field!r}")
                type_name = schema[field]
            value = parse_scalar(cond.raw_value, type_name)
            prepared.append((field, op, value))
        return prepared

    def _match(self, row: dict[str, Any], prepared_where: list[tuple[str, str, Any]]) -> bool:
        for field, op, value in prepared_where:
            left = row.get(field)
            if op == "=":
                if left != value:
                    return False
            elif op == "!=":
                if left == value:
                    return False
            elif op == ">":
                if left is None or value is None or not (left > value):
                    return False
            elif op == "<":
                if left is None or value is None or not (left < value):
                    return False
            elif op == ">=":
                if left is None or value is None or not (left >= value):
                    return False
            elif op == "<=":
                if left is None or value is None or not (left <= value):
                    return False
            else:
                raise ValidationError(f"Неподдерживаемый оператор: {op!r}")
        return True

    @handle_db_errors
    @log_time
    @log_command
    def insert(self, table: str, values: dict[str, str]) -> dict[str, Any]:
        ensure_identifier(table, what="таблицы")
        table_info = self._get_table(table)
        schema: dict[str, str] = table_info.get("schema", {})

        missing = [f for f in schema.keys() if f not in values]
        extra = [f for f in values.keys() if f not in schema]
        if missing:
            raise ValidationError(f"Не заполнены поля: {', '.join(missing)}")
        if extra:
            raise ValidationError(f"Лишние поля: {', '.join(extra)}")

        row: dict[str, Any] = {}
        for field, type_name in schema.items():
            row[field] = parse_scalar(values[field], type_name)

        table_info["last_id"] = int(table_info.get("last_id", 0)) + 1
        row["id"] = table_info["last_id"]

        rows = load_table(self.db_root, table)
        rows.append(row)
        save_table(self.db_root, table, rows)
        self._save_meta()
        self._touch(table)
        print(f"OK: добавлена запись id={row['id']}.")
        return dict(row)

    @handle_db_errors
    @log_time
    @log_command
    def select(self, table: str, where: Optional[list[Condition]] = None) -> SelectResult:
        ensure_identifier(table, what="таблицы")
        self._get_table(table)  # validate existence

        prepared_where = self._coerce_where(table, where)
        where_key = str([(f, op, repr(v)) for f, op, v in prepared_where])

        def compute() -> list[dict[str, Any]]:
            rows = load_table(self.db_root, table)
            if not prepared_where:
                return [dict(r) for r in rows]
            return [dict(r) for r in rows if self._match(r, prepared_where)]

        version = self._versions.get(table, 0)
        res = self._select_cached(table, where_key, version, compute)
        return res

    @handle_db_errors
    @log_time
    @log_command
    def update(
        self,
        table: str,
        set_values: dict[str, str],
        where: Optional[list[Condition]] = None,
    ) -> int:
        ensure_identifier(table, what="таблицы")
        table_info = self._get_table(table)
        schema: dict[str, str] = table_info.get("schema", {})

        if not set_values:
            raise ValidationError("Команда update требует set")

        prepared_set: dict[str, Any] = {}
        for field, raw in set_values.items():
            if field == "id":
                raise ValidationError("Поле 'id' нельзя изменять")
            if field not in schema:
                raise ValidationError(f"Неизвестное поле в set: {field!r}")
            prepared_set[field] = parse_scalar(raw, schema[field])

        prepared_where = self._coerce_where(table, where)

        rows = load_table(self.db_root, table)
        updated = 0
        for r in rows:
            if not prepared_where or self._match(r, prepared_where):
                for f, v in prepared_set.items():
                    r[f] = v
                updated += 1

        save_table(self.db_root, table, rows)
        self._touch(table)
        print(f"OK: обновлено записей: {updated}.")
        return updated

    @handle_db_errors
    @log_time
    @log_command
    def delete(self, table: str, where: Optional[list[Condition]] = None) -> int:
        ensure_identifier(table, what="таблицы")
        self._get_table(table)

        prepared_where = self._coerce_where(table, where)

        if not prepared_where:
            # confirm full wipe
            from .decorators import ask_confirm  # local import to avoid cycles

            if not ask_confirm("Удалить ВСЕ записи?"):
                print("Отменено.")
                return 0

        rows = load_table(self.db_root, table)
        before = len(rows)
        if not prepared_where:
            rows = []
        else:
            rows = [r for r in rows if not self._match(r, prepared_where)]
        deleted = before - len(rows)
        save_table(self.db_root, table, rows)
        self._touch(table)
        print(f"OK: удалено записей: {deleted}.")
        return deleted
from __future__ import annotations

import argparse
import shlex
from pathlib import Path
from typing import Any

from .engine import DBEngine, EngineError
from .schema import SchemaError
from .storage import StorageError


def _root_dir() -> Path:
    # корень проекта = каталог, где запускается CLI
    return Path.cwd()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="simpledb", add_help=True)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_create = sub.add_parser("create-table", help="Создать таблицу")
    p_create.add_argument("table")
    p_create.add_argument("schema", nargs="+", help="Поля в формате field:type")

    p_drop = sub.add_parser("drop-table", help="Удалить таблицу")
    p_drop.add_argument("table")

    sub.add_parser("list-tables", help="Список таблиц и схем")

    p_insert = sub.add_parser("insert", help="Добавить запись")
    p_insert.add_argument("table")
    p_insert.add_argument("pairs", nargs="+", help="Пары field=value")

    p_select = sub.add_parser("select", help="Выбрать записи")
    p_select.add_argument("table")
    p_select.add_argument("--where", default=None)

    p_update = sub.add_parser("update", help="Обновить записи")
    p_update.add_argument("table")
    p_update.add_argument("--set", required=True, help="field=value,field=value")
    p_update.add_argument("--where", default=None)

    p_delete = sub.add_parser("delete", help="Удалить записи")
    p_delete.add_argument("table")
    p_delete.add_argument("--where", default=None)
    p_delete.add_argument("--yes", action="store_true", help="Подтвердить удаление без вопросов")

    args = parser.parse_args(argv)

    engine = DBEngine.open(_root_dir())

    try:
        _dispatch(engine, args)
    except (EngineError, SchemaError, StorageError, ValueError) as exc:
        print(f"Ошибка: {exc}")


def _dispatch(engine: DBEngine, args: argparse.Namespace) -> None:
    if args.cmd == "create-table":
        engine.create_table(args.table, args.schema)
        print(f"Таблица создана: {args.table}")
        return

    if args.cmd == "drop-table":
        engine.drop_table(args.table)
        print(f"Таблица удалена: {args.table}")
        return

    if args.cmd == "list-tables":
        tables = engine.list_tables()
        if not tables:
            print("Таблиц нет")
            return
        for name, fields in tables.items():
            schema = " ".join([f"{k}:{v}" for k, v in fields.items()])
            print(f"{name}: {schema}")
        return

    if args.cmd == "insert":
        pairs = _parse_pairs(args.pairs)
        row = engine.insert(args.table, pairs)
        print(f"Добавлено: {row}")
        return

    if args.cmd == "select":
        rows = engine.select(args.table, args.where)
        if not rows:
            print("Пусто")
            return
        for row in rows:
            print(row)
        return

    if args.cmd == "update":
        set_pairs = _parse_set(args.set)
        count = engine.update(args.table, set_pairs, args.where)
        print(f"Обновлено записей: {count}")
        return

    if args.cmd == "delete":
        if args.where is None and not args.yes:
            raise ValueError("Удаление всей таблицы требует флаг --yes")
        count = engine.delete(args.table, args.where)
        print(f"Удалено записей: {count}")
        return

    raise ValueError(f"Неизвестная команда: {args.cmd}")


def _parse_pairs(parts: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for part in parts:
        if "=" not in part:
            raise ValueError(f"Ожидался формат field=value, получено: {part!r}")
        field, raw = part.split("=", 1)
        field = field.strip()
        raw = raw.strip()
        if not field:
            raise ValueError("Имя поля не может быть пустым")

        # разрешаем кавычки как в shell: name="Alice Bob"
        # если raw пустой, считаем это пустой строкой
        raw_clean = _strip_quotes(raw)
        out[field] = raw_clean
    return out


def _parse_set(text: str) -> dict[str, str]:
    items = [s.strip() for s in text.split(",") if s.strip()]
    if not items:
        raise ValueError("Параметр --set не должен быть пустым")
    return _parse_pairs(items)


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and ((value[0] == value[-1] == '"') or (value[0] == value[-1] == "'")):
        return value[1:-1]
    return value

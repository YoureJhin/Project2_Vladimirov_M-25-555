"""Парсер пользовательских команд (create_table/insert/select/update/delete и where/set)."""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass
from typing import Optional

from .errors import ParseError
from .utils import Condition, parse_assignment, parse_column_spec, parse_comparison, split_outside_quotes


@dataclass(frozen=True)
class Command:
    """Результат парсинга пользовательского ввода (имя команды и параметры).
"""
    name: str
    table: Optional[str] = None
    columns: Optional[list[tuple[str, str]]] = None  # (field, type_name)
    values: Optional[dict[str, str]] = None  # field -> raw_value
    set_values: Optional[dict[str, str]] = None  # field -> raw_value
    where: Optional[list[Condition]] = None


_UPDATE_RE = re.compile(
    r"^update\s+(?P<table>\w+)\s+set\s+(?P<set>.+?)(?:\s+where\s+(?P<where>.+))?$",
    flags=re.IGNORECASE | re.DOTALL,
)
_SELECT_RE = re.compile(
    r"^select\s+(?P<table>\w+)(?:\s+where\s+(?P<where>.+))?$",
    flags=re.IGNORECASE | re.DOTALL,
)
_DELETE_RE = re.compile(
    r"^delete\s+(?P<table>\w+)(?:\s+where\s+(?P<where>.+))?$",
    flags=re.IGNORECASE | re.DOTALL,
)


def _parse_where(where_raw: str) -> list[Condition]:
    where_raw = where_raw.strip()
    if not where_raw:
        return []
    tokens = shlex.split(where_raw, posix=True)
    parts: list[str] = []
    buf: list[str] = []
    for tok in tokens:
        if tok.lower() == "and":
            if not buf:
                raise ParseError("Некорректное условие where: пустая часть перед AND")
            parts.append(" ".join(buf))
            buf = []
        elif tok.lower() == "or":
            raise ParseError("Оператор OR не поддерживается (используйте AND).")
        else:
            buf.append(tok)
    if buf:
        parts.append(" ".join(buf))

    return [parse_comparison(p) for p in parts]


def parse_command(line: str) -> Command:
    """Парсит строку из REPL и возвращает структуру Command.

    Бросает ParseError при неверном синтаксисе.
    """
    line = line.strip()
    if not line:
        raise ParseError("Пустая команда")

    lowered = line.lower()

    if lowered in {"exit", "quit"}:
        return Command(name="exit")

    if lowered == "help":
        return Command(name="help")

    if lowered == "list_tables":
        return Command(name="list_tables")

    if lowered.startswith("create_table"):
        tokens = shlex.split(line, posix=True)
        if len(tokens) < 3:
            raise ParseError("Синтаксис: create_table <table> <field:type> ...")
        _, table, *cols = tokens
        columns = [parse_column_spec(c) for c in cols]
        return Command(name="create_table", table=table, columns=columns)

    if lowered.startswith("drop_table"):
        tokens = shlex.split(line, posix=True)
        if len(tokens) != 2:
            raise ParseError("Синтаксис: drop_table <table>")
        _, table = tokens
        return Command(name="drop_table", table=table)

    m = _SELECT_RE.match(line)
    if m:
        table = m.group("table")
        where_raw = m.group("where")
        where = _parse_where(where_raw) if where_raw else None
        return Command(name="select", table=table, where=where)

    if lowered.startswith("insert"):
        tokens = shlex.split(line, posix=True)
        if len(tokens) < 3:
            raise ParseError("Синтаксис: insert <table> <field=value> ...")
        _, table, *assignments = tokens
        values: dict[str, str] = {}
        for a in assignments:
            field, raw = parse_assignment(a)
            values[field] = raw
        return Command(name="insert", table=table, values=values)

    m = _UPDATE_RE.match(line)
    if m:
        table = m.group("table")
        set_raw = m.group("set")
        where_raw = m.group("where")
        set_values: dict[str, str] = {}
        for part in split_outside_quotes(set_raw, sep=","):
            field, raw = parse_assignment(part)
            set_values[field] = raw
        where = _parse_where(where_raw) if where_raw else None
        return Command(name="update", table=table, set_values=set_values, where=where)

    m = _DELETE_RE.match(line)
    if m:
        table = m.group("table")
        where_raw = m.group("where")
        where = _parse_where(where_raw) if where_raw else None
        return Command(name="delete", table=table, where=where)

    raise ParseError(f"Неизвестная команда: {line.split()[0]!r}")

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


class TypeErrorDB(ValueError):
    """Ошибка преобразования значения к типу схемы."""


@dataclass(frozen=True)
class FieldType:
    name: str
    cast: Callable[[str], Any]


def _to_bool(raw: str) -> bool:
    value = raw.strip().lower()
    if value in {"true", "1", "yes", "y"}:
        return True
    if value in {"false", "0", "no", "n"}:
        return False
    raise TypeErrorDB(f"Некорректное логическое значение: {raw!r}")


SUPPORTED_TYPES: dict[str, FieldType] = {
    "str": FieldType("str", lambda s: str(s)),
    "int": FieldType("int", lambda s: int(s)),
    "float": FieldType("float", lambda s: float(s)),
    "bool": FieldType("bool", _to_bool),
}


def cast_value(type_name: str, raw: str) -> Any:
    if type_name not in SUPPORTED_TYPES:
        raise TypeErrorDB(f"Неизвестный тип поля: {type_name!r}")
    try:
        return SUPPORTED_TYPES[type_name].cast(raw)
    except Exception as exc:  # noqa: BLE001
        raise TypeErrorDB(str(exc)) from exc

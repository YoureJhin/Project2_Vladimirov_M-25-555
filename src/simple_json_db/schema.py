from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .types import SUPPORTED_TYPES, cast_value


class SchemaError(ValueError):
    """Ошибки схемы таблицы."""


@dataclass(frozen=True)
class TableSchema:
    name: str
    fields: dict[str, str]  # field -> type_name

    def validate_insert(self, data: dict[str, str]) -> dict[str, Any]:
        unknown = set(data) - set(self.fields)
        if unknown:
            raise SchemaError(f"Неизвестные поля: {sorted(unknown)}")

        missing = [f for f in self.fields if f not in data]
        if missing:
            raise SchemaError(f"Отсутствуют обязательные поля: {missing}")

        cooked: dict[str, Any] = {}
        for field, type_name in self.fields.items():
            cooked[field] = cast_value(type_name, data[field])
        return cooked

    def validate_update(self, data: dict[str, str]) -> dict[str, Any]:
        unknown = set(data) - set(self.fields)
        if unknown:
            raise SchemaError(f"Неизвестные поля: {sorted(unknown)}")

        cooked: dict[str, Any] = {}
        for field, raw in data.items():
            cooked[field] = cast_value(self.fields[field], raw)
        return cooked

    @staticmethod
    def parse_schema_parts(parts: list[str]) -> dict[str, str]:
        fields: dict[str, str] = {}
        for part in parts:
            if ":" not in part:
                raise SchemaError(f"Ожидался формат field:type, получено: {part!r}")
            field, type_name = part.split(":", 1)
            field = field.strip()
            type_name = type_name.strip()
            if not field:
                raise SchemaError("Имя поля не может быть пустым")
            if type_name not in SUPPORTED_TYPES:
                raise SchemaError(f"Тип {type_name!r} не поддерживается")
            if field == "id":
                raise SchemaError("Поле 'id' зарезервировано системой")
            if field in fields:
                raise SchemaError(f"Повтор поля: {field}")
            fields[field] = type_name
        if not fields:
            raise SchemaError("Схема должна содержать хотя бы одно поле")
        return fields

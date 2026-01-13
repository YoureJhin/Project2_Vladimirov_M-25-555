"""Исключения доменной области «примитивной базы данных»."""

from __future__ import annotations


class DBError(Exception):
    """Base class for all domain errors."""


class ParseError(DBError):
    """Ошибка разбора пользовательской команды.
"""
    pass


class TableExistsError(DBError):
    """Таблица уже существует.
"""
    pass


class TableNotFoundError(DBError):
    """Таблица не найдена.
"""
    pass


class SchemaError(DBError):
    """Ошибка схемы таблицы.
"""
    pass


class ValidationError(DBError):
    """Ошибка валидации входных данных.
"""
    pass


class StorageError(DBError):
    """Ошибка чтения/записи файлового хранилища.
"""
    pass

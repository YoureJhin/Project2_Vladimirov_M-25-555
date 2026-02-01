"""Декораторы и утилиты для CLI-приложения (обработка ошибок, логирование, подтверждения)."""

from __future__ import annotations

import datetime as _dt
import functools
import traceback
from typing import Any, Callable, TypeVar

from .constants import log_path
from .errors import DBError

F = TypeVar("F", bound=Callable[..., Any])


def _safe_prompt_text(message: str) -> str:
    """Read arbitrary user input using `prompt` if available, otherwise input()."""
    try:
        import prompt as prompt_lib  # type: ignore

        # regex(".*") accepts any string (including empty).
        try:
            return str(prompt_lib.regex(r".*", prompt=message))
        except TypeError:
            # Fallback for a different signature.
            return str(prompt_lib.regex(r".*"))
    except Exception:
        return input(message)


def ask_confirm(message: str) -> bool:
    """Запрашивает у пользователя подтверждение (yes/no) и возвращает True/False.
"""
    raw = _safe_prompt_text(f"{message} (yes/no): ").strip().lower()
    return raw in {"y", "yes", "д", "да"}


def confirm_action(message: str) -> Callable[[F], F]:
    """Decorator factory: asks user confirmation before executing a destructive action."""

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any):  # type: ignore[no-untyped-def]
            if not ask_confirm(message):
                print("Отменено.")
                return None
            return func(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator


def handle_db_errors(func: F) -> F:
    """Catches domain errors and prints a friendly message."""

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any):  # type: ignore[no-untyped-def]
        try:
            return func(*args, **kwargs)
        except DBError as exc:
            print(f"Ошибка: {exc}")
            return None
        except KeyboardInterrupt:
            print("\nПрервано пользователем.")
            return None
        except Exception as exc:  # defensive
            print("Неожиданная ошибка.")
            traceback.print_exception(type(exc), exc, exc.__traceback__)
            return None

    return wrapper  # type: ignore[return-value]


def log_command(func: F) -> F:
    """Logs command execution to logs/commands.log."""

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any):  # type: ignore[no-untyped-def]
        # Expects instance method: args[0] is self with attribute `db_root`.
        self = args[0]
        ts = _dt.datetime.now().isoformat(timespec="seconds")
        line = f"{ts}\t{func.__name__}\targs={args[1:]}\tkwargs={kwargs}\n"
        try:
            lp = log_path(self.db_root)
            lp.parent.mkdir(parents=True, exist_ok=True)
            with lp.open("a", encoding="utf-8") as f:
                f.write(line)
        except Exception:
            # Logging must not break main flow.
            pass
        return func(*args, **kwargs)

    return wrapper  # type: ignore[return-value]

def log_time(func: F) -> F:
    """Measures execution time of a command and prints it to stdout.

    The decorator is intentionally lightweight: it should never raise and must not
    interfere with the core logic of the application.
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any):  # type: ignore[no-untyped-def]
        start = _dt.datetime.now()
        try:
            return func(*args, **kwargs)
        finally:
            elapsed = (_dt.datetime.now() - start).total_seconds() * 1000.0
            # Keep output short and stable for demo recordings.
            print(f"[time] {func.__name__}: {elapsed:.2f} ms")

    return wrapper  # type: ignore[return-value]

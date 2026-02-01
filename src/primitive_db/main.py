"""Точка входа: интерактивный REPL для работы с примитивной БД."""

from __future__ import annotations

from .commands import CommandExecutor
from .core import PrimitiveDB
from .errors import ParseError
from .parser import parse_command


def _read_line() -> str:
    # Prefer `prompt` if installed, otherwise fall back to input().
    try:
        import prompt as prompt_lib  # type: ignore

        try:
            match = prompt_lib.regex(r".*", prompt="db> ")
            return match.group(0) if match else ""
        except TypeError:
            # Some versions may not support `prompt=` kwarg.
            match = prompt_lib.regex(r".*")
            return match.group(0) if match else ""
    except Exception:
        return input("db> ")


def run() -> None:
    """Запускает интерактивную консоль (REPL) и обрабатывает команды пользователя."""
    print("Primitive DB — консольная файловая база данных (JSON, без SQL).")
    print("Введите help для списка команд. exit — выход.")
    db = PrimitiveDB()
    executor = CommandExecutor(db)

    while True:
        try:
            line = _read_line().strip()
        except EOFError:
            print()
            break

        if not line:
            continue

        try:
            cmd = parse_command(line)
        except ParseError as exc:
            print(f"Ошибка: {exc}")
            continue

        try:
            should_continue = executor.execute(cmd)
        except ParseError as exc:
            print(f"Ошибка: {exc}")
            continue

        if not should_continue:
            break


if __name__ == "__main__":
    run()

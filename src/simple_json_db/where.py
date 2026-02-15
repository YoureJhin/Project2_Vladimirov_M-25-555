from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Any, Callable


class WhereError(ValueError):
    """Ошибки условия where."""


_ALLOWED_BOOL_OPS = (ast.And, ast.Or)
_ALLOWED_CMPOPS = (ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE)


@dataclass(frozen=True)
class CompiledWhere:
    source: str
    fn: Callable[[dict[str, Any]], bool]


def compile_where(expr: str) -> CompiledWhere:
    """
    Компилирует простое булево выражение для фильтрации записей.

    Допускаются:
    - сравнения: =, !=, >, <, >=, <=  (в тексте используется Python-синтаксис: == вместо =)
    - логические связки: and, or
    - имена полей записи (name, age, active, id)
    - литералы: числа, строки, true/false
    """
    if not expr.strip():
        return CompiledWhere(expr, lambda _row: True)

    normalized = expr.strip()
    normalized = normalized.replace("=true", "==True").replace("=false", "==False")
    # для удобства: пользователи часто пишут "=". Разрешим только в контексте сравнения.
    normalized = _replace_single_equals(normalized)

    try:
        node = ast.parse(normalized, mode="eval")
    except SyntaxError as exc:
        raise WhereError(f"Некорректное выражение where: {exc.msg}") from exc

    _validate_ast(node)

    code = compile(node, filename="<where>", mode="eval")

    def _predicate(row: dict[str, Any]) -> bool:
        env = {k: row.get(k) for k in row.keys()}
        env["True"] = True
        env["False"] = False
        return bool(eval(code, {"__builtins__": {}}, env))  # noqa: S307

    return CompiledWhere(expr, _predicate)


def _replace_single_equals(text: str) -> str:
    # Преобразование одиночного "=" в "==", игнорируя уже существующие "==", "!=", ">=", "<="
    out = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == "=":
            prev = text[i - 1] if i > 0 else ""
            nxt = text[i + 1] if i + 1 < len(text) else ""
            if prev in {"!", ">", "<", "="} or nxt == "=":
                out.append("=")
            else:
                out.append("==")
            i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def _validate_ast(node: ast.AST) -> None:
    for n in ast.walk(node):
        if isinstance(n, ast.Expression):
            continue
        if isinstance(n, ast.BoolOp):
            if not isinstance(n.op, _ALLOWED_BOOL_OPS):
                raise WhereError("Разрешены только and/or")
            continue
        if isinstance(n, ast.Compare):
            for op in n.ops:
                if not isinstance(op, _ALLOWED_CMPOPS):
                    raise WhereError("Разрешены только операции сравнения")
            continue
        if isinstance(n, ast.Name):
            # имя поля
            continue
        if isinstance(n, ast.Constant):
            # числа/строки/True/False/None
            continue
        if isinstance(n, (ast.Load,)):
            continue
        raise WhereError(f"Недопустимый элемент в where: {type(n).__name__}")

"""Arithmetic with a syntax tree. User text is never passed to eval or a shell."""

import ast
import math
import operator
import re

_MAX_ABS = 1_000_000_000_000
_MAX_LENGTH = 100
_MAX_NODES = 40
_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}


def calculate(expression: str) -> str:
    """Return a result or a short reason the expression was rejected."""
    if not isinstance(expression, str):
        return "Expression must be text."
    compact = "".join(expression.split())
    if not compact or len(compact) > _MAX_LENGTH:
        return "Expression is empty or too long."
    if "**" in compact:
        return "Exponentiation is not supported."
    if not re.fullmatch(r"[0-9+\-*/().]+", compact):
        return "Expression contains unsupported characters."
    try:
        tree = ast.parse(compact, mode="eval")
    except SyntaxError:
        return "Expression is not valid arithmetic."
    if sum(1 for _ in ast.walk(tree)) > _MAX_NODES:
        return "Expression is too complex."
    try:
        value = _eval(tree.body)
    except ZeroDivisionError:
        return "Division by zero."
    except ValueError as exc:
        return str(exc)
    if isinstance(value, float) and not math.isfinite(value):
        return "Result is not a finite number."
    return _format(value)


def _eval(node: ast.AST) -> int | float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        if isinstance(node.value, bool):
            raise ValueError("Only basic arithmetic is allowed.")
        if abs(node.value) > _MAX_ABS:
            raise ValueError("Number is too large.")
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = _eval(node.operand)
        result = value if isinstance(node.op, ast.UAdd) else -value
        if abs(result) > _MAX_ABS:
            raise ValueError("Number is too large.")
        return result
    if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS:
        result = _BINOPS[type(node.op)](_eval(node.left), _eval(node.right))
        if abs(result) > _MAX_ABS:
            raise ValueError("Result is too large.")
        return result
    raise ValueError("Only basic arithmetic is allowed.")


def _format(value: int | float) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, float):
        return f"{value:.10g}"
    return str(value)

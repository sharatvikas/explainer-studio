"""Safe arithmetic for spec geometry: params, point coordinates (A.x), math functions — nothing else."""
import ast
import math
import re

TEXT_KEYS = ("id", "type", "label", "text", "tex", "title", "body", "items", "code", "language", "style", "color")


class ExprError(ValueError):
    pass


FUNCS = {n: getattr(math, n) for n in ["sqrt", "sin", "cos", "tan", "asin", "acos", "atan", "atan2", "exp", "log", "radians", "degrees"]}
FUNCS.update(abs=abs, min=min, max=max)
CONSTS = {"pi": math.pi, "e": math.e}
OPS = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
    ast.Pow: lambda a, b: a**b,
    ast.Mod: lambda a, b: a % b,
}


class Env:
    def __init__(self, params: dict, points: dict):
        self.params, self.points = params, points


def _ev(n, env):
    if isinstance(n, ast.Expression):
        return _ev(n.body, env)
    if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)) and not isinstance(n.value, bool):
        return float(n.value)
    if isinstance(n, ast.BinOp) and type(n.op) in OPS:
        return OPS[type(n.op)](_ev(n.left, env), _ev(n.right, env))
    if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.USub, ast.UAdd)):
        v = _ev(n.operand, env)
        return -v if isinstance(n.op, ast.USub) else v
    if isinstance(n, ast.Name):
        if n.id in env.params:
            return float(env.params[n.id])
        if n.id in CONSTS:
            return CONSTS[n.id]
        raise ExprError(f"unknown name '{n.id}'")
    if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.attr in ("x", "y"):
        if n.value.id not in env.points:
            raise ExprError(f"unknown point '{n.value.id}'")
        return float(env.points[n.value.id][0 if n.attr == "x" else 1])
    if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in FUNCS and not n.keywords:
        return float(FUNCS[n.func.id](*[_ev(a, env) for a in n.args]))
    raise ExprError(f"not allowed in expressions: {type(n).__name__}")


def evaluate(e, env: Env) -> float:
    if isinstance(e, (int, float)) and not isinstance(e, bool):
        return float(e)
    try:
        return _ev(ast.parse(str(e), mode="eval"), env)
    except ExprError:
        raise
    except Exception as ex:
        raise ExprError(f"bad expression '{e}': {ex}") from ex


def _strings(obj: dict):
    def walk(v):
        if isinstance(v, str):
            yield v
        elif isinstance(v, (list, tuple)):
            for x in v:
                yield from walk(x)
        elif isinstance(v, dict):
            for x in v.values():
                yield from walk(x)

    for k, v in obj.items():
        if k not in TEXT_KEYS:
            yield from walk(v)


def refs(obj: dict, ids: set) -> set:
    out = set()
    for s in _strings(obj):
        if s in ids:
            out.add(s)
        out.update(m for m in re.findall(r"\b([A-Za-z_]\w*)\.[xy]\b", s) if m in ids)
    out.discard(obj["id"])
    return out


def params_used(obj: dict, params: set) -> set:
    names = set()
    for s in _strings(obj):
        names.update(re.findall(r"(?<![.\w])([A-Za-z_]\w*)(?![.\w(])", s))
    return names & params


def order_objects(objects: list[dict]) -> list[dict]:
    ids = {o["id"] for o in objects}
    by = {o["id"]: o for o in objects}
    done, temp, out = set(), [], []

    def visit(i):
        if i in done:
            return
        if i in temp:
            raise ExprError("cycle: " + " → ".join(temp[temp.index(i):] + [i]))
        temp.append(i)
        for r in sorted(refs(by[i], ids)):
            visit(r)
        temp.pop()
        done.add(i)
        out.append(by[i])

    for o in objects:
        visit(o["id"])
    return out

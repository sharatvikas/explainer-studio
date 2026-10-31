"""Numeric and symbolic checks used to vet answers before a video is made.

Expressions are validated against a small arithmetic grammar *before* sympy sees
them (sympy's parser evaluates Python), so a check file can never run code.
"""
import ast
import json
from pathlib import Path

import numpy as np
import sympy as sp

FUNCS = {"sqrt": sp.sqrt, "sin": sp.sin, "cos": sp.cos, "tan": sp.tan, "asin": sp.asin, "acos": sp.acos, "atan": sp.atan,
         "exp": sp.exp, "log": sp.log, "Abs": sp.Abs, "abs": sp.Abs, "pi": sp.pi, "E": sp.E}
ALLOWED = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant, ast.Name, ast.Call, ast.Load,
           ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.USub, ast.UAdd, ast.Mod)


class VerifyError(ValueError):
    pass


def parse(expr: str, positive: bool = False):
    tree = ast.parse(str(expr), mode="eval")
    for n in ast.walk(tree):
        if not isinstance(n, ALLOWED):
            raise VerifyError(f"not allowed: {type(n).__name__}")
        if isinstance(n, ast.Constant) and not isinstance(n.value, (int, float)):
            raise VerifyError("only numbers are allowed as constants")
        if isinstance(n, ast.Name) and n.id.startswith("_"):
            raise VerifyError(f"bad name {n.id}")
        if isinstance(n, ast.Call) and not (isinstance(n.func, ast.Name) and n.func.id in FUNCS):
            raise VerifyError("only math functions may be called")
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and n.id not in FUNCS}
    local = dict(FUNCS)
    local.update({k: sp.Symbol(k, positive=True) if positive else sp.Symbol(k) for k in names})
    return sp.sympify(str(expr), locals=local)


def _num(expr, subs=None, positive=False):
    e = parse(expr, positive)
    if subs:
        e = e.subs({sp.Symbol(k, positive=positive) if positive else sp.Symbol(k): v for k, v in subs.items()})
    return float(sp.N(e))


def _one(c: dict) -> dict:
    kind, tol = c["kind"], float(c.get("tol", 1e-6))
    pos = bool(c.get("assume_positive"))
    if kind == "value":
        got, exp = _num(c["expr"], c.get("subs"), pos), float(c["expect"])
        return {"kind": kind, "ok": abs(got - exp) <= tol * max(1, abs(exp)), "got": got, "expected": exp}
    if kind == "equal":
        a, b = _num(c["a"], c.get("subs"), pos), _num(c["b"], c.get("subs"), pos)
        return {"kind": kind, "ok": abs(a - b) <= tol * max(1, abs(b)), "got": a, "expected": b}
    if kind == "symbolic_equal":
        diff = sp.simplify(parse(c["a"], pos) - parse(c["b"], pos))
        return {"kind": kind, "ok": diff == 0, "got": str(diff), "expected": "0"}
    if kind == "minimum":
        x = sp.Symbol(c["var"])
        f = sp.lambdify(x, parse(c["f"]).subs({sp.Symbol(k): v for k, v in c.get("subs", {}).items()}), "numpy")
        lo, hi = c["range"]
        xs = np.linspace(lo, hi, 2001)
        ys = np.asarray(f(xs), dtype=float)
        i = int(np.nanargmin(ys))
        from scipy.optimize import minimize_scalar

        a, b = xs[max(0, i - 1)], xs[min(len(xs) - 1, i + 1)]
        at = float(minimize_scalar(lambda v: float(f(v)), bounds=(a, b), method="bounded").x) if b > a else float(xs[i])
        ok = abs(at - float(c["expect_at"])) <= tol * max(1, abs(float(c["expect_at"])))
        res = {"kind": kind, "ok": ok, "got": at, "expected": float(c["expect_at"]), "min_value": float(f(at))}
        if "expect_value" in c:
            res["ok"] = ok and abs(float(f(at)) - float(c["expect_value"])) <= tol * max(1, abs(float(c["expect_value"])))
        return res
    raise VerifyError(f"unknown check kind '{kind}'")


def verify(checks: list[dict]) -> dict:
    results = []
    for c in checks:
        try:
            results.append(_one(c))
        except Exception as e:  # report, never crash the batch
            results.append({"kind": c.get("kind"), "ok": False, "error": f"{type(e).__name__}: {e}"})
    return {"ok": all(r["ok"] for r in results) and bool(results), "results": results}


def verify_file(path: Path) -> dict:
    path = Path(path)
    res = verify(json.loads(path.read_text(encoding="utf-8")))
    path.with_name(path.stem + ".result.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    return res

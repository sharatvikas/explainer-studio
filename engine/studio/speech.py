"""Turn on-screen symbols and LaTeX into words the narrator can say.

Specs should already write `say` in words (`studio check` warns otherwise); this is
the safety net so a stray symbol is spoken, not skipped or spelled out.
"""
import re

GREEK = ["alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta", "theta", "iota", "kappa", "lambda", "mu",
         "nu", "xi", "pi", "rho", "sigma", "tau", "upsilon", "phi", "chi", "psi", "omega"]
GREEK_CHARS = dict(zip("αβγδεζηθικλμνξπρστυφχψω", GREEK)) | dict(zip("ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΠΡΣΤΥΦΧΨΩ", [f"capital {g}" for g in GREEK]))
GREEK_CHARS.update({"Δ": "delta", "ℓ": "ell", "ϕ": "phi", "ϑ": "theta"})
SUBSCRIPTS = dict(zip("₀₁₂₃₄₅₆₇₈₉", ["nought", "1", "2", "3", "4", "5", "6", "7", "8", "9"]))
FUNCS = {"sin": "sine", "cos": "cos", "tan": "tan", "log": "log", "ln": "natural log", "exp": "exp", "lim": "the limit"}
SYMBOLS = [
    ("√", " root "), ("≠", " is not equal to "), ("≈", " approximately "), ("≤", " at most "), ("≥", " at least "),
    ("°", " degrees "), ("→", " to "), ("×", " times "), ("·", " times "), ("÷", " divided by "), ("±", " plus or minus "),
    ("−", " minus "), ("–", " minus "), ("=", " equals "), ("+", " plus "), ("<", " less than "), (">", " greater than "),
    ("∞", " infinity "), ("∝", " is proportional to "), ("%", " percent "),
    ("²", " squared"), ("³", " cubed"),
]


def _latex(text: str) -> str:
    # innermost-first so nested fractions/roots read naturally
    for _ in range(6):
        new = re.sub(r"\\d?frac\{([^{}]*)\}\{([^{}]*)\}", r" \1 over \2 ", text)
        new = re.sub(r"\\sqrt\{([^{}]*)\}", r" root \1 ", new)
        if new == text:
            break
        text = new
    text = re.sub(r"\\(times|cdot)\b", " times ", text)
    text = re.sub(r"\\(pm)\b", " plus or minus ", text)
    text = re.sub(r"\\(approx)\b", " approximately ", text)
    text = re.sub(r"\\(neq|ne)\b", " is not equal to ", text)
    text = re.sub(r"\\(leq|le)\b", " at most ", text)
    text = re.sub(r"\\(geq|ge)\b", " at least ", text)
    text = re.sub(r"\\(rightarrow|to)\b", " to ", text)
    text = re.sub(r"\\circ\b", " degrees ", text)
    text = re.sub(r"\\(" + "|".join(FUNCS) + r")\b", lambda m: f" {FUNCS[m.group(1)]} ", text)
    text = re.sub(r"\\([A-Z][a-z]+)\b", lambda m: f" {'delta' if m.group(1) == 'Delta' else 'capital ' + m.group(1).lower()} ", text)
    text = re.sub(r"\\(" + "|".join(GREEK + ["ell"]) + r")\b", r" \1 ", text)
    text = re.sub(r"\\(mathrm|text|mathbf|vec|hat)\{([^{}]*)\}", r" \2 ", text)
    text = re.sub(r"\\(left|right)\b", " ", text)
    text = re.sub(r"\\[a-zA-Z]+", " ", text)
    return text


def spoken(text: str) -> str:
    text = _latex(text)
    text = re.sub(r"\^\{?2\}?", " squared ", text)
    text = re.sub(r"\^\{?3\}?", " cubed ", text)
    text = re.sub(r"\^\{?([A-Za-z0-9]+)\}?", r" to the power \1 ", text)
    text = re.sub(r"_\{?0\}?", " nought ", text)
    text = re.sub(r"_\{?([A-Za-z0-9]+)\}?", r" sub \1 ", text)
    for ch, word in SUBSCRIPTS.items():
        text = text.replace(ch, f" {word} ")
    for ch, word in GREEK_CHARS.items():
        text = text.replace(ch, f" {word} ")
    for sym, word in SYMBOLS:
        text = text.replace(sym, word)
    # "1/eta", "x/2" → over; leave unit pairs like km/min alone
    text = re.sub(r"(?<![A-Za-z])([0-9.]+|\b[A-Za-z])\s*/\s*", r"\1 over ", text)
    text = re.sub(r"[{}$\\]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def has_symbols(say: str) -> bool:
    """True if narration still contains maths markup the writer should spell out."""
    return bool(re.search(r"[$\\^_{}]", say))

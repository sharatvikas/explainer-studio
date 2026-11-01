"""Series catalogue: a planned list of videos (topic, question, answer) checked and written as an editable CSV.

The CSV is a normal source file: `/explainer-studio:make series/<slug>` ingests it like any other table.
"""
import csv
import re
from pathlib import Path

TEMPLATES = {"worked-problem", "concept-explainer", "quiz", "facts-list", "timeline", "compare"}
KINDS = {"concept": "concept-explainer", "problem": "worked-problem", "quiz": "quiz", "facts": "facts-list",
         "timeline": "timeline", "compare": "compare"}
OUTPUTS = {"long", "short", "thumb"}
COLUMNS = ["id", "title", "kind", "template", "outputs", "difficulty", "source", "question", "answer", "key_points",
           "hook", "notes"]


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60].rstrip("-")


def _norm(title: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", title.lower()))


def _existing(paths) -> tuple[set, set]:
    """Ids (folder names) and normalised titles (lines of a text file) that already exist."""
    ids, titles = set(), set()
    for p in map(Path, paths or []):
        if p.is_dir():
            ids |= {d.name for d in p.iterdir() if d.is_dir()}
        elif p.is_file():
            titles |= {_norm(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()}
    return ids, titles


def _text(v) -> str:
    return "; ".join(map(str, v)) if isinstance(v, list) else str(v or "").strip()


def validate(data: dict, exclude=None) -> tuple[list[dict], list[str], list[str]]:
    """Returns (rows, errors, warnings). Rows are CSV-ready dicts with ids and templates filled in."""
    rows, errors, warnings, seen = [], [], [], set()
    ex_ids, ex_titles = _existing(exclude)
    items = data.get("items") if isinstance(data, dict) else data
    if not items:
        return [], ["catalogue has no items"], []
    for n, it in enumerate(items, 1):
        r = {c: _text(it.get(c)) for c in COLUMNS}
        r["id"] = slug(r["id"] or r["title"])
        where = f"item {n} ({r['id']})" if r["id"] else f"item {n}"
        if not r["title"]:
            errors.append(f"{where}: title is required")
        if not r["question"]:
            errors.append(f"{where}: question is required")
        kind = r["kind"].lower() or "concept"
        if kind not in KINDS:
            errors.append(f"{where}: kind '{kind}' (use one of {', '.join(KINDS)})")
        r["kind"] = kind
        if kind in {"problem", "quiz"} and not r["answer"]:
            errors.append(f"{where}: problems need an answer")
        r["template"] = r["template"] or KINDS.get(kind, "")
        if r["template"] not in TEMPLATES:
            errors.append(f"{where}: template '{r['template']}' (use one of {', '.join(sorted(TEMPLATES))})")
        outs = [o.strip() for o in re.split(r"[;,+ ]+", r["outputs"]) if o.strip()]
        if bad := [o for o in outs if o not in OUTPUTS]:
            errors.append(f"{where}: unknown outputs {bad} (use long, short, thumb)")
        r["outputs"] = "+".join(outs)
        if r["id"]:
            if r["id"] in seen:
                errors.append(f"duplicate id '{r['id']}'")
            seen.add(r["id"])
            if r["id"] in ex_ids or _norm(r["title"]) in ex_titles:
                warnings.append(f"{where}: '{r['title']}' already exists — pick a different angle or drop it")
        rows.append(r)
    return rows, errors, warnings


def write_csv(rows: list[dict], out_dir: Path) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "catalogue.csv"
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8-sig", newline="") as f:  # BOM so Excel opens Unicode correctly
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)
    tmp.replace(path)
    return path

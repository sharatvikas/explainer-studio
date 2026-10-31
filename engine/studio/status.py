"""Item states derived from files on disk, so a batch can resume after any interruption."""
import hashlib
import json
from pathlib import Path

from .post import FINAL_SIZE, is_done, probe


def spec_sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:16]


def _final_ok(w: Path, fmt: str, spec_mtime: float) -> bool:
    """A render counts only if it's final resolution, has its timeline, and is newer than the spec."""
    if fmt == "thumb":
        f = w / "thumb.png"
        return f.exists() and f.stat().st_mtime >= spec_mtime
    f, tl = w / f"{fmt}.raw.mp4", w / f"{fmt}.timeline.json"
    if not (f.exists() and tl.exists()) or f.stat().st_mtime < spec_mtime:
        return False
    try:
        return probe(f)[:2] == FINAL_SIZE[fmt]
    except Exception:
        return False


def _checked(w: Path) -> bool:
    m, spec = w / "check.ok", w / "spec.json"
    if not (m.exists() and spec.exists()):
        return False
    try:
        return json.loads(m.read_text(encoding="utf-8")).get("spec_sha") == spec_sha(spec)
    except (ValueError, AttributeError):
        return False


def states(root: Path) -> list[dict]:
    root = Path(root)
    plan = json.loads((root / "work" / "plan.json").read_text(encoding="utf-8"))
    rows = []
    for it in plan["items"]:
        w, o = root / "work" / it["id"], root / "output" / it["id"]
        spec = w / "spec.json"
        missing = [f for f in it["outputs"] if not (spec.exists() and _final_ok(w, f, spec.stat().st_mtime))]
        if is_done(o, it["outputs"]):
            st, missing = "done", []
        elif (w / "NEEDS_ATTENTION.md").exists():
            st = "needs-attention"
        elif spec.exists() and _checked(w) and not missing:
            st = "rendered"
        elif _checked(w):
            st = "checked"
        elif spec.exists():
            st = "spec"
        else:
            st = "planned"
        rows.append({"id": it["id"], "title": it["title"], "outputs": it["outputs"], "state": st, "missing": missing})
    return rows

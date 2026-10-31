import os
from dataclasses import dataclass
from pathlib import Path


def data_dir() -> Path:
    p = Path(os.environ.get("STUDIO_DATA") or Path.home() / ".explainer-studio")
    p.mkdir(parents=True, exist_ok=True)
    return p


def models_dir() -> Path:
    p = data_dir() / "models"
    p.mkdir(parents=True, exist_ok=True)
    return p


@dataclass(frozen=True)
class Workspace:
    root: Path
    input: Path
    work: Path
    output: Path


def workspace(root: Path) -> Workspace:
    root = Path(root).resolve()
    ws = Workspace(root, root / "input", root / "work", root / "output")
    for d in (ws.input, ws.work, ws.output):
        d.mkdir(parents=True, exist_ok=True)
    return ws

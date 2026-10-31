"""Kokoro voice model files: resumable download + SHA-256 verification."""
import hashlib
import urllib.request
from pathlib import Path

from .paths import models_dir

BASE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
FILES = [
    {"name": "kokoro-v1.0.onnx", "sha256": "7d5df8ecf7d4b1878015a32686053fd0eebe2bc377234608764cc0ef3636a6c5"},
    {"name": "voices-v1.0.bin", "sha256": "bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d"},
]


def sha_ok(path: Path, digest: str) -> bool:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest() == digest


def present() -> bool:
    d = models_dir()
    return all((d / f["name"]).exists() for f in FILES)


def download(log=print) -> None:
    d = models_dir()
    for f in FILES:
        target = d / f["name"]
        if target.exists() and sha_ok(target, f["sha256"]):
            log(f"{f['name']}: ok")
            continue
        part = target.with_suffix(target.suffix + ".part")
        for attempt in range(3):
            have = part.stat().st_size if part.exists() else 0
            req = urllib.request.Request(BASE + f["name"], headers={"Range": f"bytes={have}-"} if have else {})
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    total = have + int(r.headers.get("Content-Length", 0))
                    mode = "ab" if have and r.status == 206 else "wb"
                    done, next_pct = (have if mode == "ab" else 0), 10
                    with open(part, mode) as out:
                        for chunk in iter(lambda: r.read(1 << 20), b""):
                            out.write(chunk)
                            done += len(chunk)
                            if total and done * 100 // total >= next_pct:
                                log(f"{f['name']}: {next_pct}%")
                                next_pct += 10
                break
            except OSError as e:
                log(f"{f['name']}: retry {attempt + 1} after {e}")
        if not sha_ok(part, f["sha256"]):
            part.unlink(missing_ok=True)
            raise RuntimeError(f"{f['name']} failed checksum; run `studio models` again")
        part.replace(target)
        log(f"{f['name']}: downloaded")

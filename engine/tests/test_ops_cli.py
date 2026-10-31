import json
from pathlib import Path

from studio import cli, models, post


def test_checksum_constants_present():
    assert len(models.FILES) == 2 and all(len(f["sha256"]) == 64 for f in models.FILES)


def test_verify_file_detects_corruption(tmp_path):
    f = tmp_path / "x.bin"
    f.write_bytes(b"hello")
    assert not models.sha_ok(f, "0" * 64)
    import hashlib

    assert models.sha_ok(f, hashlib.sha256(b"hello").hexdigest())


def _plan(tmp_path, items):
    (tmp_path / "work").mkdir(exist_ok=True)
    (tmp_path / "work" / "plan.json").write_text(json.dumps({"items": items}), encoding="utf-8")


def test_status_reports_states(tmp_path, capsys):
    _plan(tmp_path, [{"id": "a", "title": "A", "template": "quiz", "outputs": ["short"]},
                     {"id": "b", "title": "B", "template": "quiz", "outputs": ["short"]},
                     {"id": "c", "title": "C", "template": "quiz", "outputs": ["short"]},
                     {"id": "d", "title": "D", "template": "quiz", "outputs": ["short"]}])
    (tmp_path / "output" / "a").mkdir(parents=True)
    (tmp_path / "output" / "a" / "short.mp4").write_bytes(b"x")
    (tmp_path / "output" / "a" / "done.json").write_text('{"outputs": ["short"]}', encoding="utf-8")
    (tmp_path / "work" / "c").mkdir()
    (tmp_path / "work" / "c" / "spec.json").write_text("{}", encoding="utf-8")
    (tmp_path / "work" / "d").mkdir()
    (tmp_path / "work" / "d" / "NEEDS_ATTENTION.md").write_text("answer disagrees", encoding="utf-8")
    assert cli.main(["status", str(tmp_path), "--json"]) == 0
    st = {r["id"]: r["state"] for r in json.loads(capsys.readouterr().out)}
    assert st == {"a": "done", "b": "planned", "c": "spec", "d": "needs-attention"}


def test_plan_check(tmp_path, capsys):
    _plan(tmp_path, [{"id": "a", "title": "A", "template": "quiz", "outputs": ["short"]},
                     {"id": "a", "title": "dup", "template": "nonsense", "outputs": ["short"]}])
    assert cli.main(["plan-check", str(tmp_path / "work" / "plan.json")]) == 1
    out = capsys.readouterr().out
    assert "duplicate id 'a'" in out and "unknown template 'nonsense'" in out


def test_sheet_tiles_frames(tmp_path):
    clip = post.make_test_clip(tmp_path / "long.raw.mp4", seconds=2, size=(640, 360))
    out = cli.main(["sheet", str(clip), "--out", str(tmp_path / "sheet.png")])
    from PIL import Image

    assert out == 0 and Image.open(tmp_path / "sheet.png").size[0] > 640


def test_doctor_reports_json(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("STUDIO_DATA", str(tmp_path))
    cli.main(["doctor", "--json", "--quick"])
    rep = json.loads(capsys.readouterr().out)
    names = {c["name"] for c in rep["checks"]}
    assert {"python", "manim", "fonts", "ffmpeg", "models", "data_dir"} <= names
    models_check = next(c for c in rep["checks"] if c["name"] == "models")
    assert not models_check["ok"] and "studio models" in models_check["fix"]

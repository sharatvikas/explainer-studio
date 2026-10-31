from pathlib import Path

from studio.checks import check

FIX = Path(__file__).parent / "fixtures" / "specs"


def kinds(r):
    return {w["kind"] for w in r["warnings"]}


def test_clean_spec_passes(monkeypatch, tmp_path):
    monkeypatch.setenv("STUDIO_FAKE_TTS", "1")
    monkeypatch.setenv("STUDIO_DATA", str(tmp_path))
    r = check(FIX / "clean.json")
    assert r["ok"] and not r["warnings"], r
    assert r["est_seconds"]["long"] > 3


def test_overflow_is_reported(monkeypatch, tmp_path):
    monkeypatch.setenv("STUDIO_FAKE_TTS", "1")
    monkeypatch.setenv("STUDIO_DATA", str(tmp_path))
    r = check(FIX / "overflow.json", fmts=("long",))
    assert {"offscreen", "overlap"} <= kinds(r)
    assert all(w["hint"] for w in r["warnings"])


def test_clutter_tiny_text_and_long_sentence(monkeypatch, tmp_path):
    monkeypatch.setenv("STUDIO_FAKE_TTS", "1")
    monkeypatch.setenv("STUDIO_DATA", str(tmp_path))
    r = check(FIX / "cluttered.json", fmts=("long",))
    assert {"clutter", "tiny_text", "too_long_say"} <= kinds(r)


def test_unknown_reference_is_error(monkeypatch, tmp_path):
    monkeypatch.setenv("STUDIO_FAKE_TTS", "1")
    monkeypatch.setenv("STUDIO_DATA", str(tmp_path))
    p = tmp_path / "s.json"
    p.write_text('{"id":"x","title":"x","beats":[{"say":"hi","do":[{"op":"show","ids":["nope"]}]}]}', encoding="utf-8")
    r = check(p)
    assert not r["ok"] and "nope" in r["errors"][0]


def test_callouts_do_not_pile_up(monkeypatch, tmp_path):
    monkeypatch.setenv("STUDIO_FAKE_TTS", "1")
    monkeypatch.setenv("STUDIO_DATA", str(tmp_path))
    r = check(FIX / "clean.json", fmts=("long",))
    # beat 1 adds a callout; by the end of beat 2 it must be gone
    assert "Pythagoras" not in r["visible_text"]["long"][2]


def test_cli_check_writes_marker(monkeypatch, tmp_path):
    import shutil

    from studio import cli

    monkeypatch.setenv("STUDIO_FAKE_TTS", "1")
    monkeypatch.setenv("STUDIO_DATA", str(tmp_path / "data"))
    spec = tmp_path / "item" / "spec.json"
    spec.parent.mkdir()
    shutil.copyfile(FIX / "clean.json", spec)
    assert cli.main(["check", str(spec)]) == 0
    assert (spec.parent / "check.ok").exists()


def test_short_flags_small_text_and_dead_space(monkeypatch, tmp_path):
    monkeypatch.setenv("STUDIO_FAKE_TTS", "1")
    monkeypatch.setenv("STUDIO_DATA", str(tmp_path / "data"))
    p = tmp_path / "s.json"
    p.write_text('{"id":"s","title":"s","objects":[{"id":"t","type":"text","text":"tiny","at":[5,3],"size":14}],'
                 '"beats":[{"say":"look","do":[{"op":"show","ids":["t"]}]}],"short":{"hook":["H"],"beats":[0]}}', encoding="utf-8")
    r = check(p, fmts=("short",))
    assert {"tiny_text", "dead_space"} <= kinds(r)

"""Regression tests for the final-review findings."""
import json
import os
from pathlib import Path

import pytest

from studio import speech


@pytest.mark.parametrize("src, must, must_not", [
    (r"$\sin\theta = 1/\eta$", ["sine", "theta", "equals", "1 over eta"], ["$", "\\"]),
    (r"$a \times b$", ["a times b"], []),
    (r"\frac{\sqrt{2}}{2}", ["root 2 over 2"], ["{"]),
    ("30°C", ["30 degrees C"], []),
    ("φ − σ = Δx, v₀", ["phi", "minus", "sigma", "equals", "delta", "v nought"], ["−", "₀"]),
    ("x^3 and r^n", ["x cubed", "r to the power n"], ["^"]),
    ("speed in km/min", ["km/min"], []),
])
def test_spoken_handles_maths(src, must, must_not):
    s = speech.spoken(src)
    for m in must:
        assert m in s, (src, s)
    for m in must_not:
        assert m not in s, (src, s)


def test_check_warns_on_symbols_in_say(monkeypatch, tmp_path):
    from studio.checks import check

    monkeypatch.setenv("STUDIO_FAKE_TTS", "1")
    monkeypatch.setenv("STUDIO_DATA", str(tmp_path / "d"))
    p = tmp_path / "s.json"
    p.write_text(json.dumps({"id": "s", "title": "s", "beats": [{"say": r"So $\sin r = 1/\eta$ here.", "do": []}]}), encoding="utf-8")
    assert "symbols_in_say" in {w["kind"] for w in check(p, ("long",))["warnings"]}


def test_caption_fonts_chosen_per_word(tmp_path):
    from studio import fonts, post

    tl = {"voice": [{"t": 0, "dur": 1, "text": "x", "caption": "ऊर्जा η"}]}
    items = post.caption_pngs(tl, tmp_path, 1080, {})
    assert items and fonts.font_file_for("ऊर्जा", "heading") != fonts.font_file_for("η", "heading")


def test_tts_cache_write_is_atomic(monkeypatch, tmp_path):
    from studio import voice

    monkeypatch.setenv("STUDIO_FAKE_TTS", "1")
    monkeypatch.setenv("STUDIO_DATA", str(tmp_path))
    calls = []
    real = os.replace
    monkeypatch.setattr(voice.os, "replace", lambda a, b: (calls.append((Path(a).name, Path(b).name)), real(a, b)))
    path, _ = voice.tts("hello there", "am_michael", 1.0)
    assert calls and calls[0][1] == path.name and calls[0][0] != path.name


def _plan(root, outputs):
    (root / "work" / "a").mkdir(parents=True)
    (root / "work" / "plan.json").write_text(json.dumps({"items": [{"id": "a", "title": "A", "template": "quiz", "outputs": outputs}]}), encoding="utf-8")
    spec = root / "work" / "a" / "spec.json"
    spec.write_text('{"id":"a"}', encoding="utf-8")
    return root / "work" / "a"


def test_status_needs_every_output_at_final_resolution(tmp_path):
    from studio import post
    from studio.status import states

    w = _plan(tmp_path, ["long", "short"])
    post.make_test_clip(w / "long.raw.mp4", seconds=1, size=(1920, 1080))
    (w / "long.timeline.json").write_text("{}", encoding="utf-8")
    st = states(tmp_path)[0]
    assert st["state"] != "rendered" and st["missing"] == ["short"]
    post.make_test_clip(w / "short.raw.mp4", seconds=1, size=(540, 960))  # a preview-sized file must not count
    (w / "short.timeline.json").write_text("{}", encoding="utf-8")
    assert states(tmp_path)[0]["missing"] == ["short"]


def test_status_treats_edited_spec_as_unchecked(tmp_path):
    from studio import cli
    from studio.status import states

    w = _plan(tmp_path, ["short"])
    (w / "check.ok").write_text(json.dumps({"spec_sha": "old"}), encoding="utf-8")
    assert states(tmp_path)[0]["state"] == "spec"


@pytest.mark.slow
def test_preview_does_not_overwrite_final_name(tmp_path, monkeypatch):
    from studio import brand, render

    monkeypatch.setenv("STUDIO_FAKE_TTS", "1")
    monkeypatch.setenv("STUDIO_DATA", str(tmp_path / "d"))
    fix = Path(__file__).parent / "fixtures" / "specs" / "clean.json"
    out = render.render(fix, "long", "preview", brand.Brand(channel_name="T"), tmp_path)
    assert out.name == "long.preview.mp4" and not (tmp_path / "long.raw.mp4").exists()


@pytest.mark.slow
def test_thumbnail_is_full_hd(tmp_path, monkeypatch):
    from PIL import Image

    from studio import brand, render

    monkeypatch.setenv("STUDIO_FAKE_TTS", "1")
    monkeypatch.setenv("STUDIO_DATA", str(tmp_path / "d"))
    fix = Path(__file__).parent / "fixtures" / "specs" / "clean.json"
    out = render.render(fix, "thumb", "final", brand.Brand(channel_name="T"), tmp_path)
    assert Image.open(out).size == (1920, 1080)


def test_end_card_fits_long_url(tmp_path, monkeypatch):
    import studio.scene as scn
    from manim import tempconfig

    from studio import brand
    from studio import spec as S
    from studio.layout import frame_config

    monkeypatch.setenv("STUDIO_FAKE_TTS", "1")
    monkeypatch.setenv("STUDIO_DATA", str(tmp_path / "d"))
    sp = S.Spec(id="e", title="e", beats=[S.Beat(say="bye")])
    b = brand.Brand(channel_name="Example Physics Channel With A Long Name", channel_url="https://www.example.com/courses/jee-advanced-2027/physics")
    cls = scn.make_scene(sp, "long", b)
    with tempconfig({"media_dir": str(tmp_path), "dry_run": True, "verbosity": "ERROR", **frame_config("long", "check")}):
        sc = cls()
        sc.render()
    assert all(abs(m.get_left()[0]) <= 7.11 and abs(m.get_right()[0]) <= 7.11 for m in sc.mobjects)


def _race_spec():
    from studio import spec as S

    return S.Spec.model_validate({
        "id": "rg", "title": "T", "kits": ["physics"],
        "objects": [{"id": "A", "type": "point", "at": [0, 0]}, {"id": "B", "type": "point", "at": [6, 0]}],
        "beats": [{"say": "Go.", "do": [{"op": "race", "board": True, "routes": [{"label": "slow", "path": ["A", "B"], "speeds": [0.5]}]}]},
                  {"say": "Clear it.", "do": [{"op": "panel_clear"}, {"op": "eq", "tex": "x=1", "box": True}]}],
        "short": {"hook": ["H"], "beats": [0, 1], "cta": "Bye now."}})


def _run(sp, fmt, tmp_path, monkeypatch, spy):
    import studio.scene as scn
    from manim import tempconfig

    from studio import brand
    from studio.layout import frame_config

    monkeypatch.setenv("STUDIO_FAKE_TTS", "1")
    monkeypatch.setenv("STUDIO_DATA", str(tmp_path / "d"))
    monkeypatch.setattr(scn.SpecScene, "on_beat_end", spy)
    cls = scn.make_scene(sp, fmt, brand.Brand(channel_name="Example Physics Channel With A Long Name", channel_url="www.example.com"))
    with tempconfig({"media_dir": str(tmp_path), "dry_run": True, "verbosity": "ERROR", **frame_config(fmt, "check")}):
        sc = cls()
        sc.render()
    return sc


def test_race_winner_box_leaves_with_the_panel(tmp_path, monkeypatch):
    seen = {}

    def spy(self, beat):
        if beat.say == "Go.":
            seen["win"] = self.race_board[-1]
        else:
            seen["after"] = {id(f) for m in self.mobjects for f in m.get_family()}

    _run(_race_spec(), "long", tmp_path, monkeypatch, spy)
    assert id(seen["win"]) not in seen["after"]


def test_short_cta_does_not_cover_panel_content(tmp_path, monkeypatch):
    sp = _race_spec()
    sp.beats[1].do = [op for op in sp.beats[1].do if op.op != "panel_clear"]  # eq stacks under the board, like the real Short
    sc = _run(sp, "short", tmp_path, monkeypatch, lambda self, beat: None)
    texts = [m for top in sc.mobjects for m in top.get_family() if getattr(m, "text", "") or hasattr(m, "tex")]
    visible = [m for m in texts if m.get_fill_opacity() > 0.05]
    boxes = [(m.get_left()[0], m.get_bottom()[1], m.get_right()[0], m.get_top()[1]) for m in visible if m.get_center()[1] < -1]
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            a, b = boxes[i], boxes[j]
            assert min(a[2], b[2]) <= max(a[0], b[0]) or min(a[3], b[3]) <= max(a[1], b[1]), "panel text overlaps the CTA"


def _visible_family(sc):
    out = []
    for top in sc.mobjects:
        for m in top.get_family():
            try:
                if m.family_members_with_points() and max(max(x.get_fill_opacity(), x.get_stroke_opacity()) for x in m.family_members_with_points()) > 0.05:
                    out.append(m)
            except AttributeError:  # ValueTracker and other non-drawables
                pass
    return out


def test_boxed_equation_fully_leaves_when_panel_clears(tmp_path, monkeypatch):
    from studio import spec as S

    sp = S.Spec(id="bx", title="t", beats=[S.Beat(say="answer", do=[S.Op(op="eq", tex="x=1", box=True)]),
                                           S.Beat(say="next", do=[S.Op(op="panel_clear")])])
    seen = {}
    _run(sp, "long", tmp_path, monkeypatch, lambda self, beat: seen.__setitem__(beat.say, [getattr(m, "tex", None) for m in _visible_family(self)]))
    assert "x=1" in seen["answer"] and "x=1" not in seen["next"]


def test_short_end_shows_only_cta_in_panel(tmp_path, monkeypatch):
    sp = _race_spec()
    sp.beats[1].do = [op for op in sp.beats[1].do if op.op != "panel_clear"]
    sc = _run(sp, "short", tmp_path, monkeypatch, lambda self, beat: None)
    assert "x=1" not in [getattr(m, "tex", None) for m in _visible_family(sc)]


def test_winner_box_never_outlives_the_board_when_panel_scrolls(tmp_path, monkeypatch):
    sp = _race_spec()
    race = sp.beats[0].do[0]
    race.model_extra["routes"] = [{"label": n, "path": ["A", "B"], "speeds": [v]} for n, v in [("one", 0.5), ("two", 0.6), ("three", 0.7)]]
    sp.beats[1].do = [op for op in sp.beats[1].do if op.op != "panel_clear"]
    sp.beats[1].do[0].model_extra["tex"] = "CD=d-x=\\dfrac{\\ell}{\\sqrt{\\eta^2-1}}"
    seen = {}

    def spy(self, beat):
        vis = {id(m) for m in _visible_family(self)}
        seen[beat.say] = (id(self.race_board[0][1]) in vis, id(self.race_board[-1]) in vis or any(id(f) in vis for f in self.race_board[-1].get_family()))

    _run(sp, "short", tmp_path, monkeypatch, spy)
    board_visible, win_visible = seen["Clear it."]
    assert win_visible == board_visible


def test_short_cta_clears_reveal_leftovers(tmp_path, monkeypatch):
    from studio import spec as S

    sp = S.Spec(id="rv", title="t", beats=[S.Beat(say="first", do=[S.Op(op="eq", tex="y=2")]),
                                           S.Beat(say="big", do=[S.Op(op="reveal", text="Big idea")])],
                short=S.Short(hook=["H"], beats=[0, 1], cta="Bye."))
    sc = _run(sp, "short", tmp_path, monkeypatch, lambda self, beat: None)
    vis = _visible_family(sc)
    assert "y=2" not in [getattr(m, "tex", None) for m in vis]
    assert not any(getattr(m, "text", "").startswith("Big") for m in vis)

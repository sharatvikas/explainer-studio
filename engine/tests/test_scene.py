import json
from pathlib import Path

import pytest
from manim import tempconfig

from studio import brand, scene
from studio import spec as S

FIX = Path(__file__).parent / "fixtures" / "specs"


def run(sp, fmt, tmp_path):
    cls = scene.make_scene(sp, fmt, brand.Brand(channel_name="T"), base_dir=FIX)
    from studio.layout import frame_config

    with tempconfig({"media_dir": str(tmp_path), "dry_run": True, "disable_caching": True, "verbosity": "ERROR", **frame_config(fmt, "check")}):
        sc = cls()
        sc.render()
    return cls, sc


@pytest.mark.parametrize("fmt", ["long", "short"])
def test_all_ops_construct(tmp_path, fmt, monkeypatch):
    monkeypatch.setenv("STUDIO_FAKE_TTS", "1")
    monkeypatch.setenv("STUDIO_DATA", str(tmp_path / "data"))
    sp = S.load(FIX / "all_ops.json")
    cls, _ = run(sp, fmt, tmp_path)
    tl = json.loads((tmp_path / "timeline" / f"{cls.__name__}.json").read_text())
    expected = len(sp.beats) if fmt == "long" else len(sp.short.beats) + 1
    assert len(tl["voice"]) == expected
    if fmt == "long":
        assert tl["chapters"][0]["title"] == "Start"
    else:
        assert tl["chapters"] == []  # chapters are a long-form feature


def test_thumb_constructs(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_FAKE_TTS", "1")
    monkeypatch.setenv("STUDIO_DATA", str(tmp_path / "data"))
    _, sc = run(S.load(FIX / "all_ops.json"), "thumb", tmp_path)
    assert len(sc.mobjects) > 3


def test_unknown_op_is_clear(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_FAKE_TTS", "1")
    monkeypatch.setenv("STUDIO_DATA", str(tmp_path / "data"))
    sp = S.Spec(id="x", title="x", beats=[S.Beat(say="hi", do=[S.Op(op="explode")])])
    with pytest.raises(scene.OpError, match="unknown op 'explode'"):
        run(sp, "long", tmp_path)


def test_graph_curve_stays_whole_after_tween(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_FAKE_TTS", "1")
    monkeypatch.setenv("STUDIO_DATA", str(tmp_path / "data"))
    sp = S.Spec(id="g", title="g", params={"x": 0.0}, beats=[
        S.Beat(say="trace it", do=[S.Op(op="graph", id="g", fn="x**2", var="x", range=[0, 2], trace=True),
                                   S.Op(op="tween", param="x", to=2.0)]),
        S.Beat(say="park it", do=[S.Op(op="tween", param="x", to=1.0)])])
    _, sc = run(sp, "long", tmp_path)
    curve = sc.graphs["g"]["curve"]
    ax = sc.graphs["g"]["axes"]
    assert curve.get_end()[0] == pytest.approx(ax.c2p(2, 4)[0], abs=0.05)


def _scene(sp, fmt, tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_FAKE_TTS", "1")
    monkeypatch.setenv("STUDIO_DATA", str(tmp_path / "data"))
    return run(sp, fmt, tmp_path)[1]


def _graph_spec():
    return S.Spec(id="g2", title="g", params={"x": 0.0}, beats=[
        S.Beat(say="trace it", do=[S.Op(op="graph", id="g", fn="x**2", var="x", range=[0, 2], trace=True, x_label="x"),
                                   S.Op(op="tween", param="x", to=2.0)]),
        S.Beat(say="clear it", do=[S.Op(op="panel_clear")])])


def test_panel_clear_removes_traced_graph(tmp_path, monkeypatch):
    import studio.scene as scn

    seen = []
    monkeypatch.setattr(scn.SpecScene, "on_beat_end", lambda self, beat: seen.append(
        ({id(f) for m in self.mobjects for f in m.get_family()}, {id(self.graphs["g"][k]) for k in ("curve", "dot", "value", "axes")})))
    _scene(_graph_spec(), "long", tmp_path, monkeypatch)
    on_screen, graph_parts = seen[-1]
    assert not graph_parts & on_screen


def test_graph_labels_stay_readable(tmp_path, monkeypatch):
    sc = _scene(S.Spec(id="g3", title="g", params={"x": 0.0}, beats=[
        S.Beat(say="trace it", do=[S.Op(op="graph", id="g", fn="x**2", var="x", range=[0, 2], trace=True, x_label="x")])]),
        "long", tmp_path, monkeypatch)
    xlab = sc.graphs["g"]["frame"][1][0]
    assert xlab.height * 1080 / 8 >= 16


def test_short_ignores_camera_and_reveal_replaces_hook(tmp_path, monkeypatch):
    sp = S.Spec(id="sh", title="t", objects=[S.Obj(id="A", type="point", at=[1, 1], label="A")],
                beats=[S.Beat(say="look", do=[S.Op(op="camera", focus="stage", zoom=1.5), S.Op(op="show", ids=["A"])]),
                       S.Beat(say="big idea", do=[S.Op(op="reveal", text="Big idea")])],
                short=S.Short(hook=["HOOK"], beats=[0, 1]))
    sc = _scene(sp, "short", tmp_path, monkeypatch)
    assert sc.camera.frame.width == pytest.approx(9.0)
    assert sc.hook not in sc.mobjects


def test_callout_avoids_panel_items(tmp_path, monkeypatch):
    sp = S.Spec(id="co", title="t", beats=[S.Beat(say="eqs", do=[S.Op(op="eq", tex="a=b"), S.Op(op="eq", tex="c=d", at=0.5)]),
                                           S.Beat(say="note", do=[S.Op(op="callout", text="Look here")])])
    calls = []
    import studio.scene as scn

    orig = scn.SpecScene.on_beat_end

    def spy(self, beat):
        calls.append([(m.get_bottom()[1], m.get_top()[1]) for m in self.panel_items] + [("callout", self.transients[-1].get_top()[1]) if self.transients else None])
        orig(self, beat)

    monkeypatch.setattr(scn.SpecScene, "on_beat_end", spy)
    _scene(sp, "long", tmp_path, monkeypatch)
    items, callout_top = calls[-1][:-1], calls[-1][-1][1]
    lowest = min(b for b, _ in items)
    assert callout_top < lowest


def test_short_without_diagram_fills_middle(tmp_path, monkeypatch):
    import studio.scene as scn

    sp = S.Spec(id="q", title="q", objects=[S.Obj(id="opts", type="bullet_list", items=["A. one", "B. two", "C. three"])],
                beats=[S.Beat(say="options", do=[S.Op(op="show", ids=["opts"])]),
                       S.Beat(say="answer", do=[S.Op(op="eq", tex="a=\\dfrac{mg}{m}=g", box=True)])],
                short=S.Short(hook=["QUIZ"], beats=[0, 1]))
    sizes = {}
    monkeypatch.setattr(scn.SpecScene, "on_beat_end", lambda self, beat: sizes.setdefault(beat.say, (self.world.get("opts").height, self.panel_items[-1].height if self.panel_items else 0)))
    _scene(sp, "short", tmp_path, monkeypatch)
    assert sizes["options"][0] >= 3.0          # list fills a real share of the 16-unit-tall frame
    assert sizes["answer"][1] >= 1.2           # the boxed equation is phone-readable


def _frames(sp, fmt, tmp_path, monkeypatch, attr):
    import studio.scene as scn

    seen = {}
    monkeypatch.setattr(scn.SpecScene, "on_beat_end", lambda self, beat: seen.__setitem__(beat.say, attr(self)))
    _scene(sp, fmt, tmp_path, monkeypatch)
    return seen


def test_auto_framing_zooms_on_diagram_when_panel_empty(tmp_path, monkeypatch):
    sp = S.Spec(id="af", title="t", objects=[S.Obj(id="A", type="point", at=[1, 1], label="A"), S.Obj(id="B", type="point", at=[9, 5], label="B"),
                                             S.Obj(id="AB", type="segment", **{"from": "A", "to": "B"})],
                beats=[S.Beat(say="diagram only", do=[S.Op(op="show", ids=["A", "B", "AB"])]),
                       S.Beat(say="now maths", do=[S.Op(op="eq", tex="y=mx+c")])])
    w = _frames(sp, "long", tmp_path, monkeypatch, lambda s: s.camera.frame.width)
    assert w["diagram only"] < 12.5
    assert w["now maths"] == pytest.approx(14.222, abs=0.01)


def test_race_board_keeps_final_times_on_screen(tmp_path, monkeypatch):
    sp = S.Spec.model_validate({
        "id": "rb", "title": "T", "kits": ["physics"],
        "objects": [{"id": "A", "type": "point", "at": [0, 0]}, {"id": "B", "type": "point", "at": [6, 0]}],
        "beats": [{"say": "Go.", "do": [{"op": "race", "board": True, "routes": [{"label": "slow", "path": ["A", "B"], "speeds": [0.5]}]}]},
                  {"say": "Look at the time.", "do": []}]})
    texts = _frames(sp, "long", tmp_path, monkeypatch,
                    lambda s: [getattr(m, "text", "") for top in s.mobjects for m in top.get_family()])
    assert any(t.startswith("12.00") for t in texts["Look at the time."])

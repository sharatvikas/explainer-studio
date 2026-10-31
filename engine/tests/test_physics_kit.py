import json
from pathlib import Path

import pytest
from manim import tempconfig

from studio import brand, kits, objects, scene
from studio import spec as S
from studio.kits.physics import route_state, route_time


def test_route_time_and_state():
    pts, sp = [(0, 0), (3, 0), (3, 4)], [1.0, 0.5]
    assert route_time(pts, sp) == 3 + 8
    p, h, done = route_state(pts, sp, 20)
    assert done == 11 and tuple(p[:2]) == (3, 4)
    p, h, done = route_state(pts, sp, 1.5)
    assert done is None and tuple(p[:2]) == (1.5, 0)


def test_kit_registers_types():
    kits.load(["physics"])
    for t in ["physics.road", "physics.car", "physics.ray", "physics.media", "physics.spring", "physics.incline", "physics.pulley"]:
        assert t in objects.BUILDERS
    from studio.ops import OPS

    assert "race" in OPS


def test_unknown_kit():
    with pytest.raises(S.SpecError, match="unknown kit 'alchemy'"):
        kits.load(["alchemy"])


def test_race_runs_in_scene(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_FAKE_TTS", "1")
    monkeypatch.setenv("STUDIO_DATA", str(tmp_path / "data"))
    sp = S.Spec.model_validate({
        "id": "race", "title": "Race", "kits": ["physics"],
        "objects": [
            {"id": "road", "type": "physics.road", "from": [0, 5], "to": [10, 5]},
            {"id": "A", "type": "point", "at": [1, 5]}, {"id": "D", "type": "point", "at": [7, 5]},
            {"id": "B", "type": "point", "at": [7, 2]}, {"id": "C", "type": "point", "at": [5.27, 5]},
            {"id": "spring", "type": "physics.spring", "from": [1, 1], "to": [4, 1]},
            {"id": "ramp", "type": "physics.incline", "at": [6, 0.5], "width": 3, "angle": 30},
            {"id": "pul", "type": "physics.pulley", "center": [9, 1], "radius": 0.4},
            {"id": "ray", "type": "physics.ray", "path": ["A", "C", "B"]},
            {"id": "med", "type": "physics.media", "boundary": 5, "top_label": "fast", "bottom_label": "slow"},
        ],
        "beats": [{"say": "Which car wins the race?", "do": [
            {"op": "show", "ids": ["road", "A", "B", "spring", "ramp", "pul"]},
            {"op": "race", "board": True, "routes": [
                {"color": "bad", "label": "Straight", "path": ["A", "B"], "speeds": [0.5]},
                {"color": "good", "label": "Turn at C", "path": ["A", "C", "B"], "speeds": [1, 0.5]}]}]},
            {"say": "Light does the same.", "do": [{"op": "show", "ids": ["med"]}, {"op": "create", "ids": ["ray"]}]}],
    })
    cls = scene.make_scene(sp, "long", brand.Brand(channel_name="T"))
    with tempconfig({"media_dir": str(tmp_path), "dry_run": True, "disable_caching": True, "verbosity": "ERROR", "frame_rate": 5, "pixel_width": 320, "pixel_height": 180}):
        cls().render()
    tl = json.loads((tmp_path / "timeline" / f"{cls.__name__}.json").read_text())
    assert any(s["name"] == "win" for s in tl["sfx"])


def test_race_scoreboard_shows_world_times(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_FAKE_TTS", "1")
    monkeypatch.setenv("STUDIO_DATA", str(tmp_path / "data"))
    sp = S.Spec.model_validate({
        "id": "times", "title": "T", "kits": ["physics"],
        "objects": [{"id": "A", "type": "point", "at": [0, 0]}, {"id": "B", "type": "point", "at": [6, 0]}],
        "beats": [{"say": "Go.", "do": [{"op": "race", "board": True, "routes": [{"label": "slow", "path": ["A", "B"], "speeds": [0.5]}]}]}],
    })
    cls = scene.make_scene(sp, "long", brand.Brand(channel_name="T"))
    with tempconfig({"media_dir": str(tmp_path), "dry_run": True, "disable_caching": True, "verbosity": "ERROR", "frame_rate": 5, "pixel_width": 320, "pixel_height": 180}):
        sc = cls()
        sc.render()
    assert sc.race_results == [("slow", pytest.approx(12.0))]
    assert sc.race_board[0][2].text.startswith("12.00")

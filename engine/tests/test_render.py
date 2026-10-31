from pathlib import Path

import av
import pytest

from studio import brand, render

FIX = Path(__file__).parent / "fixtures" / "specs"


@pytest.fixture(autouse=True)
def fake_voice(monkeypatch, tmp_path):
    monkeypatch.setenv("STUDIO_FAKE_TTS", "1")
    monkeypatch.setenv("STUDIO_DATA", str(tmp_path / "data"))


@pytest.mark.slow
def test_preview_render_long(tmp_path):
    out = render.render(FIX / "clean.json", "long", "preview", brand.Brand(channel_name="T"), tmp_path)
    assert out == tmp_path / "long.preview.mp4" and out.stat().st_size > 10_000
    with av.open(str(out)) as c:
        assert (c.streams.video[0].width, c.streams.video[0].height) == (854, 480)


@pytest.mark.slow
def test_short_is_vertical(tmp_path):
    out = render.render(FIX / "clean.json", "short", "preview", brand.Brand(channel_name="T"), tmp_path)
    with av.open(str(out)) as c:
        assert (c.streams.video[0].width, c.streams.video[0].height) == (540, 960)


@pytest.mark.slow
def test_thumb_is_1920x1080_png(tmp_path):
    from PIL import Image

    out = render.render(FIX / "clean.json", "thumb", "final", brand.Brand(channel_name="T"), tmp_path)
    assert out.suffix == ".png" and Image.open(out).size == (1920, 1080)


def test_failure_writes_log(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text('{"id":"bad","title":"x","beats":[{"say":"hi","do":[{"op":"show","ids":["ghost"]}]}]}', encoding="utf-8")
    with pytest.raises(Exception):
        render.render(bad, "long", "preview", brand.Brand(channel_name="T"), tmp_path)
    assert "ghost" in (tmp_path / "render.log").read_text(encoding="utf-8")

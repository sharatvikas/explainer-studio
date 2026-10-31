import json

import pytest

from studio import post
from studio.brand import Brand

TL = {"duration": 6.0, "chapters": [{"t": 0, "title": "Intro"}, {"t": 3.0, "title": "Title"}, {"t": 3.5, "title": "Main"}],
      "voice": [{"t": 0.0, "dur": 2.0, "text": "Hello", "caption": "Hello there friend"}], "sfx": []}


@pytest.fixture(autouse=True)
def data(monkeypatch, tmp_path):
    monkeypatch.setenv("STUDIO_DATA", str(tmp_path / "data"))
    monkeypatch.setenv("STUDIO_FAKE_TTS", "1")


def item(d, fmt="long", size=(1920, 1080), seconds=2):
    d.mkdir(parents=True, exist_ok=True)
    post.make_test_clip(d / f"{fmt}.raw.mp4", seconds=seconds, size=size)
    wav = d / "v.wav"
    post.make_test_tone(wav, 1.0)
    tl = dict(TL, duration=float(seconds), voice=[dict(TL["voice"][0], wav=str(wav))])
    (d / f"{fmt}.timeline.json").write_text(json.dumps(tl), encoding="utf-8")
    return d


def test_srt_and_chapters(tmp_path):
    post.write_srt(TL, tmp_path / "s.srt")
    post.write_chapters(TL, tmp_path / "c.txt")
    assert "00:00:00,000 --> 00:00:02,000" in (tmp_path / "s.srt").read_text(encoding="utf-8")
    lines = (tmp_path / "c.txt").read_text(encoding="utf-8").splitlines()
    assert lines[0] == "0:00 Intro" and not any("Title" in l for l in lines)


def test_is_done_requires_marker(tmp_path):
    (tmp_path / "long.mp4").write_bytes(b"x")
    assert not post.is_done(tmp_path, ["long"])
    (tmp_path / "done.json").write_text(json.dumps({"outputs": ["long"]}), encoding="utf-8")
    assert post.is_done(tmp_path, ["long"])
    assert not post.is_done(tmp_path, ["long", "short"])


def test_package_long_with_spaces_and_unicode(tmp_path):
    d = item(tmp_path / "Rāj Kumar's videos" / "item 1")
    res = post.package(d, d / "out", Brand(channel_name="Example Channel", channel_url="example.com"), ["long"])
    out = d / "out"
    assert (out / "long.mp4").exists() and res["durations"]["long"] > 1.5
    assert (out / "subtitles.srt").exists() and (out / "description.txt").exists()
    assert post.is_done(out, ["long"]) and not list(out.glob("*.tmp.mp4"))
    assert post.probe(out / "long.mp4")[:2] == (1920, 1080)


def test_package_short_burns_captions(tmp_path):
    d = item(tmp_path / "s", "short", (1080, 1920))
    post.package(d, d / "out", Brand(channel_name="T"), ["short"])
    assert post.probe(d / "out" / "short.mp4")[:2] == (1080, 1920)


def test_rejects_low_resolution_final(tmp_path):
    d = item(tmp_path / "low", size=(854, 480))
    with pytest.raises(post.QualityError, match="1920x1080"):
        post.package(d, d / "out", Brand(channel_name="T"), ["long"])
    assert not (d / "out" / "done.json").exists()


def test_description_uses_research_sources(tmp_path):
    d = item(tmp_path / "r")
    (d / "spec.json").write_text(json.dumps({"id": "r", "title": "Where to Leave the Road", "kits": ["physics"], "beats": [{"say": "Three cars race."}]}), encoding="utf-8")
    (d / "research.md").write_text("## Sources\n- https://example.edu/fermat — Fermat's principle notes\n", encoding="utf-8")
    post.package(d, d / "out", Brand(channel_name="T", channel_url="https://t.example"), ["long"])
    desc = (d / "out" / "description.txt").read_text(encoding="utf-8")
    assert "Where to Leave the Road" in desc and "https://example.edu/fermat" in desc and "0:00 Intro" in desc and "#physics" in desc

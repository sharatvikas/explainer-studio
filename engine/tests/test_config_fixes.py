import json
from pathlib import Path

import pytest

from studio import brand, render
from studio.cli import main
from studio.commands import brand_from_args

FIX = Path(__file__).parent / "fixtures" / "specs"


def _args(tmp_path, cfg):
    f = tmp_path / "brand.config.json"
    f.write_text(json.dumps(cfg), encoding="utf-8")
    ap = __import__("argparse").Namespace(workspace=str(tmp_path), channel_name="", channel_url="", logo="", voice="",
                                         brand_file=str(f))
    return ap


def test_brand_file_keeps_shell_special_characters(tmp_path):
    name = 'Ravi\'s "Physics" $HOME `x` & Co'
    b = brand_from_args(_args(tmp_path, {"channel_name": name, "voice": "bm_george", "logo": ""}))
    assert b.channel_name == name and b.voice == "bm_george"


def test_brand_file_option_accepted_by_render_and_package():
    import argparse

    from studio.commands import _package_cfg, _render_cfg

    for cfg, cmd in ((_render_cfg, ["x.json", "--format", "long"]), (_package_cfg, ["d", "--out", "o"])):
        p = argparse.ArgumentParser()
        cfg(p)
        assert p.parse_args([*cmd, "--brand-file", "b.json"]).brand_file == "b.json"


def test_failure_log_is_per_format_and_survives_other_success(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text('{"id":"bad","title":"x","beats":[{"say":"hi","do":[{"op":"show","ids":["ghost"]}]}]}', encoding="utf-8")
    with pytest.raises(Exception):
        render.render(bad, "long", "preview", brand.Brand(channel_name="T"), tmp_path)
    render.render(FIX / "clean.json", "thumb", "final", brand.Brand(channel_name="T"), tmp_path)
    assert "ghost" in (tmp_path / "long.render.log").read_text(encoding="utf-8")
    assert not (tmp_path / "render.log").exists()

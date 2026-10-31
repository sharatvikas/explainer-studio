"""Environment diagnosis with plain-language fixes (Windows commands where relevant)."""
import platform
import sys
import tempfile
from pathlib import Path

WIN = platform.system() == "Windows"
RUN = 'uv run --project "<plugin>/engine" studio'


def _check(name, fn, fix):
    try:
        detail = fn()
        return {"name": name, "ok": True, "detail": detail or "", "fix": ""}
    except Exception as e:
        return {"name": name, "ok": False, "detail": f"{type(e).__name__}: {e}", "fix": fix}


def run(quick: bool = False) -> dict:
    from . import fonts, models
    from .paths import data_dir

    def py():
        assert sys.version_info[:2] == (3, 12), sys.version
        return sys.version.split()[0]

    def manim():
        import cairo  # noqa: F401
        import manim as m

        return m.__version__

    def fonts_ok():
        fonts.register()
        return ", ".join(sorted(p.name for p in fonts.DIR.glob("*.ttf")))

    def ffmpeg():
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()

    def models_ok():
        if not models.present():
            raise FileNotFoundError("voice model files missing")
        return str(Path(data_dir()) / "models")

    def writable():
        with tempfile.NamedTemporaryFile(dir=data_dir()):
            return str(data_dir())

    checks = [
        _check("python", py, "Python 3.12 is managed by uv: run `uv sync` in the plugin's engine folder"),
        _check("manim", manim, "brew install cairo pkg-config, then `uv sync`" if platform.system() == "Darwin" else "run `uv sync --reinstall` in the engine folder"),
        _check("fonts", fonts_ok, "reinstall the plugin; fonts ship in engine/studio/assets/fonts"),
        _check("ffmpeg", ffmpeg, "run `uv sync` (ffmpeg comes from the imageio-ffmpeg package)"),
        _check("models", models_ok, f"run `{RUN} models` to download the voice (~350 MB)"),
        _check("data_dir", writable, "check folder permissions for " + str(data_dir())),
    ]
    from . import fonts as F

    checks.append({"name": "hindi_text", "ok": True,
                   "detail": "complex-script shaping available" if F.complex_shaping() else
                   "WARNING: Pillow has no raqm/fribidi; Hindi (Devanagari) captions may render incorrectly. English is unaffected.",
                   "fix": ""})
    if not quick:
        def render():
            import os

            from . import brand, render as R

            os.environ["STUDIO_FAKE_TTS"] = "1"
            with tempfile.TemporaryDirectory() as t:
                spec = Path(t) / "s.json"
                spec.write_text('{"id":"doctor","title":"Doctor","beats":[{"say":"Testing one two.","do":[]}]}', encoding="utf-8")
                R.render(spec, "long", "preview", brand.Brand(channel_name="Doctor"), Path(t))
            return "preview render ok"

        checks.append(_check("render", render, "see the error above; run `/explainer-studio:doctor` for help"))
    return {"ok": all(c["ok"] for c in checks), "platform": platform.platform(), "checks": checks}

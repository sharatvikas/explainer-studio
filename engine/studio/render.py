"""Render one spec format in-process with Manim; outputs land in the item's work folder."""
import os
import shutil
import traceback
from pathlib import Path

from manim import tempconfig

from . import spec as S
from .brand import Brand, color
from .layout import frame_config
from .scene import make_scene

OUT_NAME = {"long": "long.raw.mp4", "short": "short.raw.mp4", "thumb": "thumb.png"}


def out_name(fmt: str, quality: str) -> str:
    """Finals feed packaging; previews never overwrite them."""
    return OUT_NAME[fmt] if quality == "final" or fmt == "thumb" else f"{fmt}.preview.mp4"


def render(spec_path: Path, fmt: str, quality: str, brand: Brand, out_dir: Path) -> Path:
    spec_path, out_dir = Path(spec_path), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        sp = S.load(spec_path)
        cls = make_scene(sp, fmt, brand, base_dir=spec_path.parent)
        media = out_dir / f"media_{fmt}"
        cfg = {
            **frame_config(fmt, quality),
            "media_dir": str(media), "disable_caching": True, "verbosity": "WARNING", "progress_bar": "none",
            "background_color": brand.colors.get("bg", color("bg")),
            "write_to_movie": fmt != "thumb", "save_last_frame": fmt == "thumb",
            "output_file": cls.__name__,
        }
        with tempconfig(cfg):
            sc = cls()
            sc.render()
            fw = sc.renderer.file_writer
            produced = Path(fw.image_file_path if fmt == "thumb" else fw.movie_file_path)
        target = out_dir / out_name(fmt, quality)
        tl = media / "timeline" / f"{cls.__name__}.json"
        if tl.exists() and quality == "final":
            shutil.copyfile(tl, out_dir / f"{fmt}.timeline.json")  # timeline first, video last
        tmp = target.with_name(target.stem + ".tmp" + target.suffix)
        shutil.copyfile(produced, tmp)
        os.replace(tmp, target)
        (out_dir / f"{fmt}.render.log").unlink(missing_ok=True)
        return target
    except Exception:
        tail = traceback.format_exc().splitlines()[-40:]
        (out_dir / f"{fmt}.render.log").write_text("\n".join(tail), encoding="utf-8")
        raise

"""Screen zones for 16:9 long-form and 9:16 Shorts; the same spec renders into either."""
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Box:
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def w(self):
        return self.x1 - self.x0

    @property
    def h(self):
        return self.y1 - self.y0

    @property
    def center(self):
        return np.array([(self.x0 + self.x1) / 2, (self.y0 + self.y1) / 2, 0.0])


class Layout:
    def __init__(self, fmt: str):
        self.fmt = fmt
        self.full_middle = False
        if fmt == "short":
            self.frame_w, self.frame_h = 9.0, 16.0
            self.title = Box(-4.2, 4.6, 4.2, 6.9)
            self.stage = Box(-4.1, -1.2, 4.1, 4.3)
            self.panel = Box(-4.1, -4.3, 4.1, -1.5)
            self.captions = Box(-4.3, -5.6, 4.3, -4.5)
        else:
            self.frame_w, self.frame_h = 14.222, 8.0
            self.title = Box(-6.9, 3.2, 6.9, 3.9)
            self.stage = Box(-7.0, -2.6, 0.7, 2.6)
            self.panel = Box(1.0, -3.4, 6.9, 3.4)
            self.captions = Box(-6.9, -3.9, 6.9, -3.3)
        self.full = Box(-self.frame_w / 2 + 0.4, -self.frame_h / 2 + 0.4, self.frame_w / 2 - 0.4, self.frame_h / 2 - 0.4)

    def use_full_middle(self):
        """Short with no diagram: panel content gets the whole middle (between hook and captions)."""
        self.panel = Box(-4.1, -4.3, 4.1, 4.3)
        self.full_middle = True

    def zone(self, name: str) -> Box:
        return getattr(self, name, self.stage)


def world_to_stage(stage, box: Box):
    """Map world coordinates (0..stage.width, 0..stage.height) into a screen box, keeping aspect."""
    s = min(box.w / stage.width, box.h / stage.height)
    ox = box.center[0] - stage.width * s / 2
    oy = box.center[1] - stage.height * s / 2
    return (lambda p: np.array([ox + p[0] * s, oy + p[1] * s, 0.0])), s


def fit(mob, box: Box, max_scale: float = 1.0, center: bool = True):
    """Scale `mob` down (never up past max_scale) so it fits `box`; optionally centre it there."""
    k = min(max_scale, box.w / max(mob.width, 1e-6), box.h / max(mob.height, 1e-6))
    if abs(k - 1) > 1e-9:
        mob.scale(k)
    return mob.move_to(box.center) if center else mob


def wrap(text: str, width: int) -> str:
    words, lines, cur = text.split(), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return "\n".join(lines)


def frame_config(fmt: str, quality: str = "check") -> dict:
    """Manim config for a format: frame size in units must match Layout, pixels per quality."""
    px = {
        ("long", "final"): (1920, 1080, 60), ("long", "preview"): (854, 480, 15), ("long", "check"): (320, 180, 5),
        ("short", "final"): (1080, 1920, 60), ("short", "preview"): (540, 960, 15), ("short", "check"): (180, 320, 5),
        ("thumb", "final"): (1920, 1080, 1), ("thumb", "preview"): (1280, 720, 1), ("thumb", "check"): (320, 180, 1),
    }[(fmt, quality)]
    lay = Layout("long" if fmt == "thumb" else fmt)
    return {"pixel_width": px[0], "pixel_height": px[1], "frame_rate": px[2], "frame_width": lay.frame_w, "frame_height": lay.frame_h}

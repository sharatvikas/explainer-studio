"""Brand: semantic colours, channel identity and text helpers shared by every video."""
import json
from dataclasses import dataclass, field
from pathlib import Path

from manim import BOLD, HEAVY, MEDIUM, RoundedRectangle, SurroundingRectangle, Text, VGroup

from . import fonts

SEMANTIC = {
    "primary": "#79A9F5",
    "secondary": "#F5A543",
    "accent": "#F4CF6B",
    "good": "#5ED39B",
    "bad": "#F2696B",
    "muted": "#8A93A6",
    "ink": "#E8ECF2",
    "bg": "#0B0E14",
    "road": "#58C7E3",
    "field": "#F5A543",
    "panel": "#141923",
}
_active = dict(SEMANTIC)


@dataclass
class Brand:
    channel_name: str = "My Channel"
    channel_url: str = ""
    logo: Path | None = None
    voice: str = "am_michael"
    speed: float = 1.0
    music: bool = True
    colors: dict = field(default_factory=lambda: dict(SEMANTIC))


def load(root: Path, overrides: dict) -> Brand:
    """brand.json in the workspace (optional) overlaid with plugin config values."""
    data = {}
    f = Path(root) / "brand.json"
    if f.exists():
        data = json.loads(f.read_text(encoding="utf-8"))
    data.update({k: v for k, v in overrides.items() if v not in (None, "")})
    b = Brand(**{k: v for k, v in data.items() if k in Brand.__dataclass_fields__ and k != "colors"})
    b.colors.update(data.get("colors", {}))
    if b.logo:
        b.logo = Path(b.logo)
    activate(b)
    return b


def activate(b: Brand) -> None:
    _active.clear()
    _active.update(b.colors)


def color(name: str) -> str:
    return _active.get(name, name)


def T(text, size=30, color_name="ink", weight=MEDIUM, role="body", **kw):
    fonts.register()
    return Text(text, font=fonts.family_for(text, role), font_size=size, color=color(color_name), weight=weight, **kw)


def H(text, size=46, color_name="accent", **kw):
    fonts.register()
    return Text(text, font=fonts.family_for(text, "heading"), font_size=size, color=color(color_name), weight=HEAVY, **kw)


def pill(mob, color_name="accent", buff=0.18, opacity=0.14):
    box = RoundedRectangle(corner_radius=0.12, width=mob.width + 2 * buff, height=mob.height + 2 * buff)
    return box.set_stroke(color(color_name), 2).set_fill(color(color_name), opacity).move_to(mob)


def glow_box(mob, color_name="accent", buff=0.25):
    c = color(color_name)
    inner = SurroundingRectangle(mob, color=c, buff=buff, corner_radius=0.1, stroke_width=2.5)
    halo = VGroup(*[inner.copy().set_stroke(c, width=w, opacity=o) for w, o in [(10, 0.08), (6, 0.12)]])
    return VGroup(halo, inner)


__all__ = ["Brand", "load", "activate", "color", "T", "H", "pill", "glow_box", "BOLD", "HEAVY", "MEDIUM"]

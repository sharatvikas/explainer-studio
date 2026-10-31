"""Bundled OFL fonts, chosen per text by glyph coverage (Devanagari, Greek, symbols)."""
from functools import lru_cache
from pathlib import Path

from fontTools.ttLib import TTFont
from PIL import ImageFont

DIR = Path(__file__).parent / "assets" / "fonts"
HEADING, BODY = "Poppins", "Lato"
# preference order per role; the first file covering every character wins
ROLES = {
    "heading": ["Poppins-ExtraBold.ttf", "Lato-Bold.ttf"],
    "heading-medium": ["Poppins-Bold.ttf", "Lato-Bold.ttf"],
    "medium": ["Poppins-Medium.ttf", "Lato-Regular.ttf"],
    "body": ["Lato-Regular.ttf", "Poppins-Medium.ttf"],
    "body-bold": ["Lato-Bold.ttf", "Poppins-Bold.ttf"],
}
FAMILY = {"Poppins": "Poppins", "Lato": "Lato"}
_registered = False


def register():
    """Make bundled fonts visible to Manim's Pango text renderer (idempotent)."""
    global _registered
    if _registered:
        return
    import manimpango

    for f in DIR.glob("*.ttf"):
        manimpango.register_font(str(f))
    _registered = True


@lru_cache(maxsize=None)
def _cmap(name: str) -> frozenset:
    return frozenset(TTFont(DIR / name).getBestCmap())


def covers(name: str, text: str) -> bool:
    cm = _cmap(name)
    return all(ord(ch) in cm for ch in text if not ch.isspace() and ord(ch) >= 32)


def font_file_for(text: str, role: str = "heading") -> str:
    files = ROLES.get(role, ROLES["heading"])
    return next((f for f in files if covers(f, text)), files[0])


def family_for(text: str, role: str = "heading") -> str:
    return font_file_for(text, role).split("-")[0]


def complex_shaping() -> bool:
    """Pillow's raqm engine shapes Devanagari correctly; without it conjuncts/matras break."""
    from PIL import features

    return bool(features.check("raqm"))


@lru_cache(maxsize=128)
def _font(name: str, size: int):
    if complex_shaping():
        return ImageFont.truetype(str(DIR / name), size, layout_engine=ImageFont.Layout.RAQM)
    return ImageFont.truetype(str(DIR / name), size)


def pil(role: str, size: int, text: str = ""):
    return _font(font_file_for(text, role), size)

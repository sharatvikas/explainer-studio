"""`studio check`: dry-run a spec and report layout problems as JSON — no images needed.

After every beat it looks at the text/maths on screen and reports:
  offscreen    text outside the visible frame
  overlap      two text items covering each other
  tiny_text    text whose font size is under ~26 px (long) / ~40 px (Short) at final resolution
  dead_space   a Short beat whose content covers too little of the frame
  clutter      too many text items on screen at once
  too_long_say narration sentence over 25 words
"""
import os
import tempfile
from pathlib import Path

from manim import Text, tempconfig

from . import spec as S
from .brand import Brand
from .expr import ExprError
from .mtex import M
from .objects import ObjectError
from .ops import OpError
from .layout import frame_config
from .scene import make_scene

FINAL_PX = {"long": 1080, "short": 1920}  # frame height in pixels at final quality
MAX_TEXT = {"long": 12, "short": 9}
MIN_PX = {"long": 26, "short": 40}  # em height in final pixels; Shorts are read on phones
TEXT_EM_PER_FONT_SIZE = 0.0125  # manim Text: font_size 48 ≈ 0.6 units
DEAD_SPACE_MIN_AREA = 0.30  # Short: content bbox should cover >= 30% of the middle area (8.2 x 8.6 units)
HEADLINE_PX = 80  # a beat showing a big headline this size is a deliberate "title card" moment, not dead space
MAX_WORDS = 25
HINTS = {
    "offscreen": "move it inside its zone, shorten the text, or let the panel/fit place it (drop 'at')",
    "overlap": "give one item a different 'dir'/'near'/'at', or show them in different beats",
    "tiny_text": "increase 'size', shorten the text so fitting doesn't shrink it, or split across beats",
    "clutter": "hide or panel_clear older items before adding new ones; one idea per beat",
    "too_long_say": "split the sentence into two beats (max ~22 words reads best)",
    "symbols_in_say": "write narration in words (e.g. 'sine r equals one over eta'); put maths in eq/label ops",
    "dead_space": "give the beat a visual (object, chart, card) or use bigger panel content; Shorts must fill the frame",
}


def _texts(mobs):
    """Top-level text-like mobjects (Text or maths), not their individual glyphs."""
    out = []
    for m in mobs:
        if isinstance(m, (Text, M)):
            out.append(m)
        else:
            out += _texts(m.submobjects)
    return out


def _visible(m):
    try:
        return max(max(sm.get_fill_opacity(), sm.get_stroke_opacity()) for sm in m.family_members_with_points()) > 0.05
    except (ValueError, AttributeError):  # empty, or not drawable (e.g. ValueTracker)
        return False


def _label(m):
    return getattr(m, "tex", None) or getattr(m, "text", "") or type(m).__name__


def _box(m):
    (x0, y0, _), (x1, y1, _) = m.get_corner([-1, -1, 0]), m.get_corner([1, 1, 0])
    return x0, y0, x1, y1


def _overlap(a, b):
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    w, h = min(ax1, bx1) - max(ax0, bx0), min(ay1, by1) - max(ay0, by0)
    if w <= 0 or h <= 0:
        return 0.0
    smaller = min((ax1 - ax0) * (ay1 - ay0), (bx1 - bx0) * (by1 - by0)) or 1e-9
    return w * h / smaller


class _Inspector:
    def __init__(self, fmt):
        self.fmt, self.warnings, self.visible, self.beat = fmt, [], [], -1

    def warn(self, kind, ids, detail=""):
        self.warnings.append({"beat": self.beat, "fmt": self.fmt, "kind": kind, "ids": ids, "detail": detail, "hint": HINTS[kind]})

    def inspect(self, scene, beat):
        self.beat += 1
        from .speech import has_symbols

        if has_symbols(beat.say):
            self.warn("symbols_in_say", [], beat.say[:60])
        if len(beat.say.split()) > MAX_WORDS:
            self.warn("too_long_say", [], f"{len(beat.say.split())} words")
        frame = scene.camera.frame
        fx0, fy0 = frame.get_corner([-1, -1, 0])[:2]
        fx1, fy1 = frame.get_corner([1, 1, 0])[:2]
        px_per_unit = FINAL_PX[self.fmt] / frame.height
        texts = [t for t in _texts(scene.mobjects) if _visible(t)]
        self.visible.append([_label(t) for t in texts])
        boxes = [(_label(t), _box(t), t) for t in texts]
        for name, (x0, y0, x1, y1), t in boxes:
            if x0 < fx0 - 0.02 or x1 > fx1 + 0.02 or y0 < fy0 - 0.02 or y1 > fy1 + 0.02:
                self.warn("offscreen", [name])
            em = t.em if isinstance(t, M) else t.font_size * TEXT_EM_PER_FONT_SIZE
            if em * px_per_unit < MIN_PX[self.fmt]:
                self.warn("tiny_text", [name], f"{em * px_per_unit:.0f}px")
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                if _overlap(boxes[i][1], boxes[j][1]) > 0.15:
                    self.warn("overlap", [boxes[i][0], boxes[j][0]])
        if self.fmt == "short":
            content = [m for m in scene.mobjects if m is not scene.hook and m.family_members_with_points() and _visible(m)]
            headline = any((t.em if isinstance(t, M) else t.font_size * TEXT_EM_PER_FONT_SIZE) * px_per_unit >= HEADLINE_PX
                           for t in texts if not any(t in h.get_family() for h in [scene.hook] if h is not None))
            if content and not headline:
                x0 = min(m.get_left()[0] for m in content)
                x1 = max(m.get_right()[0] for m in content)
                y0 = min(m.get_bottom()[1] for m in content)
                y1 = max(m.get_top()[1] for m in content)
                cover = (x1 - x0) * (y1 - y0) / (8.2 * 8.6)
                if cover < DEAD_SPACE_MIN_AREA:
                    self.warn("dead_space", [], f"content covers {cover:.0%} of the frame's middle")
        texts_counted = [t for t in texts if not (scene.hook is not None and t in scene.hook.get_family())]
        if len(texts_counted) > MAX_TEXT[self.fmt]:
            self.warn("clutter", [], f"{len(texts_counted)} text items on screen (max {MAX_TEXT[self.fmt]})")


def _run(sp, fmt, base_dir):
    insp = _Inspector(fmt)
    cls = make_scene(sp, fmt, Brand(channel_name="Check"), base_dir=base_dir)
    cls.on_beat_end = lambda self, beat: insp.inspect(self, beat)
    with tempfile.TemporaryDirectory() as tmp, tempconfig({
        "media_dir": tmp, "dry_run": True, "disable_caching": True, "verbosity": "ERROR",
        **frame_config(fmt, "check"),
    }):
        sc = cls()
        sc.render()
        return insp, sc.now


def check(spec_path: Path, fmts=("long", "short")) -> dict:
    os.environ.setdefault("STUDIO_FAKE_TTS", "1")
    spec_path = Path(spec_path)
    res = {"ok": True, "errors": [], "warnings": [], "est_seconds": {}, "visible_text": {}}
    try:
        sp = S.load(spec_path)
    except S.SpecError as e:
        return {**res, "ok": False, "errors": e.messages}
    for fmt in fmts:
        if fmt == "short" and not sp.short:
            continue
        try:
            insp, secs = _run(sp, fmt, spec_path.parent)
        except (ObjectError, OpError, ExprError, S.SpecError, KeyError, ValueError) as e:
            res["ok"] = False
            res["errors"].append(f"{fmt}: {type(e).__name__}: {e}")
            continue
        res["warnings"] += insp.warnings
        res["est_seconds"][fmt] = round(secs, 1)
        res["visible_text"][fmt] = insp.visible
    return res

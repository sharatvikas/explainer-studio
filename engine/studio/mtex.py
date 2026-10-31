"""LaTeX-free math typesetting: matplotlib mathtext (Computer Modern) -> Manim VMobjects.

    M(r"t = \frac{x}{v}")                     one coloured formula
    M(r"t_1", r"=\frac{x}{v}", colors=[GREEN])  parts laid out on a shared baseline,
                                                addressable as eq[0], eq[1], ...
"""
import numpy as np
import matplotlib

matplotlib.use("Agg")
matplotlib.rcParams["mathtext.fontset"] = "cm"
from matplotlib.font_manager import FontProperties
from matplotlib.path import Path
from matplotlib.textpath import TextPath
from manim import VGroup, VMobject, WHITE, ORIGIN

_FP = FontProperties(family="DejaVu Serif")
_PT = 0.03  # manim units per mathtext point at scale 1


def _glyphs(tex: str) -> VMobject:
    """One VMobject per formula; subpaths kept together so glyph holes fill correctly."""
    if not tex.startswith("$"):
        tex = f"${tex}$"
    tp = TextPath((0, 0), tex, size=10, prop=_FP)
    mob = VMobject(stroke_width=0, fill_opacity=1)
    verts, codes = tp.vertices * _PT, tp.codes
    cur = None
    i = 0
    while i < len(codes):
        c = codes[i]
        p = np.array([*verts[i], 0.0])
        if c == Path.MOVETO:
            mob.start_new_path(p)
            cur = p
            i += 1
        elif c == Path.LINETO:
            mob.add_line_to(p)
            cur = p
            i += 1
        elif c == Path.CURVE3:
            ctrl, end = p, np.array([*verts[i + 1], 0.0])
            mob.add_cubic_bezier_curve_to(cur + 2 / 3 * (ctrl - cur), end + 2 / 3 * (ctrl - end), end)
            cur = end
            i += 2
        elif c == Path.CURVE4:
            c1, c2, end = p, np.array([*verts[i + 1], 0.0]), np.array([*verts[i + 2], 0.0])
            mob.add_cubic_bezier_curve_to(c1, c2, end)
            cur = end
            i += 3
        elif c == Path.CLOSEPOLY:
            mob.close_path()
            i += 1
        else:  # STOP
            i += 1
    return mob, tp.get_extents()


class M(VGroup):
    def __init__(self, *parts, colors=None, color=WHITE, scale=1.0, gap=0.06, **kw):
        super().__init__(**kw)
        self.tex = "".join(parts)
        x = 0.0
        colors = colors or []
        for k, tex in enumerate(parts):
            g, ext = _glyphs(tex)
            g.shift([x - ext.x0 * _PT, 0, 0])
            g.set_fill(colors[k] if k < len(colors) and colors[k] else color, 1)
            self.add(g)
            x += ext.width * _PT + gap
        self.scale(scale, about_point=ORIGIN)
        self.center()
        # em size tracks later scaling (used by layout QA to judge readability)
        self._em0, self._h0 = 0.266 * scale, max(self.height, 1e-6)

    @property
    def em(self) -> float:
        return self._em0 * self.height / self._h0

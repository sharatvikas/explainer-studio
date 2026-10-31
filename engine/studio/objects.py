"""Spec objects → Manim mobjects.

Never use MathTex, Tex, DecimalNumber, Integer, BarChart, Table defaults or
Axes.add_coordinates here: they need a LaTeX install. Maths goes through
mtex.M, numbers and words through brand.T.
"""
import numpy as np
from manim import (
    DOWN, LEFT, RIGHT, UP, Angle, Arc, Arrow, Axes, Brace, Circle, Code, DashedLine, Dot, DoubleArrow, ImageMobject,
    Line, NumberLine, Polygon, Rectangle, RoundedRectangle, ValueTracker, VGroup, VMobject, always_redraw,
)

from . import layout as L
from .brand import BOLD, MEDIUM, H, T, color
from .expr import Env, evaluate, order_objects, params_used, refs
from .mtex import M

DIRS = {"up": UP, "down": DOWN, "left": LEFT, "right": RIGHT, "ur": UP + RIGHT, "ul": UP + LEFT, "dr": DOWN + RIGHT, "dl": DOWN + LEFT}
BUILDERS = {}
# object types placed into a zone (panel/stage) rather than at world coordinates
ZONED = {"bullet_list", "card", "code", "table", "axes", "bar_chart", "line_chart", "number_line", "timeline", "flow"}


class ObjectError(ValueError):
    pass


def register(name):
    def deco(fn):
        BUILDERS[name] = fn
        return fn

    return deco


class World:
    """Resolves spec objects in dependency order; param-driven ones redraw every frame."""

    def __init__(self, spec, lay: L.Layout, base_dir=None):
        self.spec, self.layout, self.base_dir = spec, lay, base_dir
        self.objs = [o.model_dump(by_alias=True) for o in spec.objects]
        self.by_id = {o["id"]: o for o in self.objs}
        self.params = {k: ValueTracker(v) for k, v in spec.params.items()}
        self.to_screen, self.scale = L.world_to_stage(spec.stage, lay.stage)
        self.mobs: dict = {}
        self.axes: dict = {}
        self.text_scale = 1.4 if lay.fmt == "short" else 1.0
        if lay.fmt == "short" and not any(self._on_stage(o) for o in self.objs):
            lay.use_full_middle()  # no diagram: panel content takes the whole middle of the Short
        for o in self.objs:
            if o["type"] not in BUILDERS:
                raise ObjectError(f"unknown object type '{o['type']}' (object '{o['id']}')")
        self.order = order_objects(self.objs)
        ids, pnames = set(self.by_id), set(self.params)
        self.dynamic = set()
        for o in self.order:
            if params_used(o, pnames) or refs(o, ids) & self.dynamic:
                self.dynamic.add(o["id"])

    @staticmethod
    def _on_stage(o) -> bool:
        if o["type"] in ZONED:
            return o.get("zone") == "stage" or "at" in o
        return not (o["type"] == "text" and "at" not in o)

    # -- geometry -------------------------------------------------------------
    def env(self) -> Env:
        pts = {}
        env = Env({k: v.get_value() for k, v in self.params.items()}, pts)
        for o in self.order:
            if o["type"] == "point":
                pts[o["id"]] = (evaluate(o["at"][0], env), evaluate(o["at"][1], env))
        return env

    def world_xy(self, ref, env=None):
        env = env or self.env()
        if isinstance(ref, str):
            if ref not in env.points:
                raise ObjectError(f"'{ref}' is not a point")
            return env.points[ref]
        return (evaluate(ref[0], env), evaluate(ref[1], env))

    def xy(self, ref) -> np.ndarray:
        return self.to_screen(self.world_xy(ref))

    def point(self, pid) -> np.ndarray:
        return self.xy(pid)

    def length(self, world_units: float) -> float:
        return world_units * self.scale

    # -- building ---------------------------------------------------------------
    def make(self, o):
        mob = BUILDERS[o["type"]](o, self)
        if o["type"] in ZONED and "at" not in o:
            zone = self.layout.zone(o.get("zone", "panel"))
            L.fit(mob, zone, max_scale=2.2 if self.layout.fmt == "short" else 1.0)
        return mob

    def build(self):
        for o in self.order:
            if o["id"] in self.dynamic:
                self.mobs[o["id"]] = always_redraw(lambda o=o: self.make(o))
            else:
                self.mobs[o["id"]] = self.make(o)

    def get(self, oid):
        if oid not in self.mobs:
            raise ObjectError(f"unknown object id '{oid}'")
        return self.mobs[oid]


def c(o, default="ink"):
    return color(o.get("color", default))


def _label(tex, at, direction, col, size=1.0):
    return M(tex, color=col, scale=size).next_to(at, direction, buff=0.12)


# ---- geometry -------------------------------------------------------------------
@register("point")
def _point(o, w):
    p = w.point(o["id"])
    d = Dot(p, radius=0.07, color=c(o))
    if not o.get("label"):
        return d
    return VGroup(d, _label(o["label"], d, DIRS[o.get("label_dir", "up")], c(o), o.get("label_size", 1.0) * w.text_scale))


@register("segment")
def _segment(o, w):
    cls = DashedLine if o.get("dashed") else Line
    return cls(w.xy(o["from"]), w.xy(o["to"])).set_stroke(c(o), o.get("width", 5))


@register("polyline")
def _polyline(o, w):
    return VMobject().set_points_as_corners([w.xy(p) for p in o["path"]]).set_stroke(c(o), o.get("width", 5))


@register("arrow")
def _arrow(o, w):
    return Arrow(w.xy(o["from"]), w.xy(o["to"]), buff=0, color=c(o), stroke_width=o.get("width", 5))


@register("vector")
def _vector(o, w):
    a, b = w.xy(o["from"]), w.xy(o["to"])
    arr = Arrow(a, b, buff=0, color=c(o, "primary"), stroke_width=o.get("width", 6))
    if not o.get("label"):
        return arr
    d = (b - a) / max(np.linalg.norm(b - a), 1e-6)
    normal = np.array([-d[1], d[0], 0])
    return VGroup(arr, M(o["label"], color=c(o, "primary"), scale=w.text_scale).move_to((a + b) / 2 + normal * 0.35))


REGION_STYLE = {"plain": ("muted", 0.15), "water": ("#16304A", 1), "glass": ("#1E3A55", 1), "grass": ("#14261C", 1), "hatched": ("bg", 0)}


@register("region")
def _region(o, w):
    pts = [w.xy(p) for p in o["corners"]]
    style = o.get("style", "plain")
    fill, op = REGION_STYLE.get(style, ("muted", 0.15))
    poly = Polygon(*pts).set_fill(color(o.get("color", fill)), op).set_stroke(width=0)
    if style == "grass":
        rng = np.random.default_rng(3)
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        tufts = VGroup()
        for _ in range(int((max(xs) - min(xs)) * (max(ys) - min(ys)) * 6)):
            x0, y0 = rng.uniform(min(xs) + 0.05, max(xs) - 0.05), rng.uniform(min(ys) + 0.05, max(ys) - 0.15)
            h = rng.uniform(0.05, 0.1)
            tufts.add(*[Line([x0, y0, 0], [x0 + dx, y0 + h, 0]) for dx in (-0.03, 0, 0.03)])
        return VGroup(poly, tufts.set_stroke("#2F5A3E", 1.6, opacity=0.8))
    if style == "hatched":
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        lines = VGroup(*[Line([x, min(ys), 0], [x + (max(ys) - min(ys)), max(ys), 0]) for x in np.arange(min(xs) - (max(ys) - min(ys)), max(xs), 0.25)])
        return VGroup(poly.set_stroke(c(o, "muted"), 1.5), lines.set_stroke(c(o, "muted"), 1, 0.35))
    return poly


@register("circle")
def _circle(o, w):
    return Circle(radius=w.length(o["radius"])).move_to(w.xy(o["center"])).set_stroke(c(o), o.get("width", 4)).set_fill(c(o), o.get("fill", 0))


@register("arc")
def _arc(o, w):
    return Arc(radius=w.length(o["radius"]), start_angle=np.radians(o.get("start", 0)), angle=np.radians(o.get("end", 90) - o.get("start", 0)), arc_center=w.xy(o["center"])).set_stroke(c(o), o.get("width", 4))


@register("angle")
def _angle(o, w):
    v = w.xy(o["vertex"])
    p1 = w.xy(o["from"]) if "from" in o else v + np.array([*o.get("from_dir", [1, 0]), 0.0])
    p2 = w.xy(o["to"]) if "to" in o else v + np.array([*o.get("to_dir", [0, 1]), 0.0])
    d1, d2 = p1 - v, p2 - v
    l1, l2 = Line(v, p1), Line(v, p2)
    if d1[0] * d2[1] - d1[1] * d2[0] < 0:  # always draw the smaller angle, counter-clockwise
        l1, l2 = l2, l1
    arc = Angle(l1, l2, radius=o.get("radius", 0.6)).set_stroke(c(o, "accent"), 3)
    if not o.get("label"):
        return arc
    mid = arc.point_from_proportion(0.5)
    return VGroup(arc, M(o["label"], color=c(o, "accent"), scale=w.text_scale).move_to(v + (mid - v) * 1.55))


@register("dimension")
def _dimension(o, w):
    off = DIRS[o.get("side", "up")] * o.get("offset", 0.45)
    a, b = w.xy(o["from"]) + off, w.xy(o["to"]) + off
    arr = DoubleArrow(a, b, buff=0, stroke_width=2.5, tip_length=0.16, color=c(o, "muted"))
    if not o.get("label"):
        return arr
    return VGroup(arr, M(o["label"], color=c(o), scale=w.text_scale).next_to(arr, DIRS[o.get("side", "up")], buff=0.08))


@register("brace")
def _brace(o, w):
    br = Brace(Line(w.xy(o["from"]), w.xy(o["to"])), DIRS[o.get("side", "up")], buff=o.get("offset", 0.2), color=c(o, "accent"))
    if not o.get("label"):
        return br
    lab = T(o["label"], 26, o.get("color", "accent"), BOLD) if o.get("plain") else M(o["label"], color=c(o, "accent"), scale=w.text_scale)
    return VGroup(br, lab.next_to(br, DIRS[o.get("side", "up")], buff=0.08))


@register("label")
def _label_obj(o, w):
    m = M(o["tex"], color=c(o), scale=o.get("size", 1.0) * w.text_scale)
    return m.move_to(w.xy(o["at"]) + DIRS.get(o.get("dir", ""), 0 * UP) * o.get("offset", 0.35))


@register("text")
def _text(o, w):
    m = T(L.wrap(o["text"], o.get("wrap", 40)), o.get("size", 30), o.get("color", "ink"), BOLD if o.get("bold") else MEDIUM)
    if "at" in o:
        return m.move_to(w.xy(o["at"]))
    return L.fit(m, w.layout.zone(o.get("zone", "panel")))


# ---- zoned content ----------------------------------------------------------------
@register("bullet_list")
def _bullets(o, w):
    if o.get("style") == "cards":  # quiz options: equal-width rounded cards
        texts = [T(L.wrap(item, o.get("wrap", 26)), o.get("size", 32), "ink", BOLD) for item in o["items"]]
        width = max(t.width for t in texts) + 0.8
        cards = VGroup()
        for t in texts:
            bg = RoundedRectangle(corner_radius=0.18, width=width, height=t.height + 0.55)
            bg.set_fill(color("panel"), 1).set_stroke(color(o.get("color", "primary")), 2)
            cards.add(VGroup(bg, t.move_to(bg).align_to(bg, LEFT).shift(RIGHT * 0.4)))
        return cards.arrange(DOWN, buff=0.3)
    rows = VGroup()
    for i, item in enumerate(o["items"]):
        dot = Dot(radius=0.07, color=color(o.get("color", "accent")))
        txt = T(L.wrap(item, o.get("wrap", 34)), o.get("size", 30))
        rows.add(VGroup(dot, txt.next_to(dot, RIGHT, buff=0.25, aligned_edge=UP).shift(UP * 0.06)))
    return rows.arrange(DOWN, aligned_edge=LEFT, buff=0.35)


@register("card")
def _card(o, w):
    title = H(o.get("title", ""), o.get("title_size", 36), o.get("color", "accent"))
    body = T(L.wrap(o.get("body", ""), o.get("wrap", 30)), o.get("size", 28))
    content = VGroup(title, body).arrange(DOWN, aligned_edge=LEFT, buff=0.25)
    bg = RoundedRectangle(corner_radius=0.2, width=content.width + 0.7, height=content.height + 0.6)
    bg.set_fill(color("panel"), 1).set_stroke(color(o.get("color", "accent")), 2)
    return VGroup(bg, content.move_to(bg))


@register("code")
def _code(o, w):
    return Code(code_string=o["code"], language=o.get("language", "python"), background="rectangle", add_line_numbers=o.get("line_numbers", True))


@register("table")
def _table(o, w):
    rows = o["rows"]
    cells = [[T(str(v), o.get("size", 26), "accent" if r == 0 else "ink", BOLD if r == 0 else MEDIUM) for v in row] for r, row in enumerate(rows)]
    ncol = max(len(r) for r in cells)
    colw = [max(cells[r][k].width for r in range(len(cells)) if k < len(cells[r])) + 0.5 for k in range(ncol)]
    rowh = max(cell.height for row in cells for cell in row) + 0.35
    g = VGroup()
    for r, row in enumerate(cells):
        x = 0.0
        for k, cell in enumerate(row):
            cell.move_to([x + colw[k] / 2, -r * rowh, 0])
            g.add(cell)
            x += colw[k]
    total = sum(colw)
    g.add(Line([0, -rowh / 2, 0], [total, -rowh / 2, 0]).set_stroke(color("muted"), 1.5))
    return g


def _axes(o):
    x, y = o.get("x", [0, 10]), o.get("y", [0, 10])
    ax = Axes(
        x_range=[x[0], x[1], (x[1] - x[0]) / 4], y_range=[y[0], y[1], (y[1] - y[0]) / 4],
        x_length=o.get("width", 5.6), y_length=o.get("height", 3.6),
        axis_config={"color": color("muted"), "stroke_width": 2, "include_ticks": False}, tips=True,
    )
    labels = VGroup()
    k = o.get("label_size", 1.25)
    if o.get("x_label"):
        labels.add(M(o["x_label"], color=color("ink"), scale=k).next_to(ax.x_axis.get_end(), DOWN, buff=0.15))
    if o.get("y_label"):
        labels.add(M(o["y_label"], color=color("ink"), scale=k).next_to(ax.y_axis.get_end(), LEFT, buff=0.15))
    return ax, labels


@register("axes")
def _axes_obj(o, w):
    ax, labels = _axes(o)
    w.axes[o["id"]] = ax
    return VGroup(ax, labels)


@register("bar_chart")
def _bars(o, w):
    vals, labs = o["values"], o["labels"]
    top = max(vals) or 1
    palette = ["primary", "secondary", "good", "accent", "bad"]
    g = VGroup()
    for i, (v, lab) in enumerate(zip(vals, labs)):
        h = 3.0 * v / top
        bar = Rectangle(width=0.8, height=max(h, 0.02)).set_fill(color(palette[i % 5]), 1).set_stroke(width=0)
        bar.move_to([i * 1.2, h / 2, 0])
        g.add(VGroup(bar, T(str(lab), 24).next_to(bar, DOWN, buff=0.15), T(f"{v:g}", 24, "ink", BOLD).next_to(bar, UP, buff=0.1)))
    return g


@register("line_chart")
def _line_chart(o, w):
    xs, ys = o["x"], o["y"]
    ax, labels = _axes({"x": [min(xs), max(xs)], "y": [min(0, min(ys)), max(ys) * 1.1], **{k: o[k] for k in ("x_label", "y_label") if k in o}})
    curve = VMobject().set_points_smoothly([ax.c2p(a, b) for a, b in zip(xs, ys)]).set_stroke(c(o, "accent"), 4)
    w.axes[o["id"]] = ax
    return VGroup(ax, labels, curve)


@register("number_line")
def _number_line(o, w):
    a, b = o.get("range", [-5, 5])
    nl = NumberLine(x_range=[a, b, o.get("step", 1)], length=o.get("length", 8), include_numbers=False, color=color("muted"))
    nums = VGroup(*[T(f"{v:g}", 22, "muted").next_to(nl.n2p(v), DOWN, buff=0.15) for v in np.arange(a, b + 1e-9, o.get("step", 1))])
    return VGroup(nl, nums)


@register("timeline")
def _timeline(o, w):
    ev = o["events"]
    n = len(ev)
    span = 1.8 * max(n - 1, 1)
    line = Line([0, 0, 0], [span, 0, 0]).set_stroke(color("muted"), 3)
    g = VGroup(line)
    for i, e in enumerate(ev):
        x = span * i / max(n - 1, 1)
        g.add(VGroup(Dot([x, 0, 0], radius=0.1, color=color("accent")),
                     T(str(e.get("date", "")), 26, "accent", BOLD).move_to([x, 0.45, 0]),
                     T(L.wrap(e.get("text", ""), 14), 22).next_to([x, -0.25, 0], DOWN, buff=0.05)))
    return g


@register("flow")
def _flow(o, w):
    nodes = VGroup()
    for name in o["nodes"]:
        txt = T(L.wrap(name, 14), o.get("size", 26), "ink", BOLD)
        box = RoundedRectangle(corner_radius=0.15, width=txt.width + 0.5, height=txt.height + 0.4)
        box.set_fill(color("panel"), 1).set_stroke(color(o.get("color", "primary")), 2)
        nodes.add(VGroup(box, txt.move_to(box)))
    direction = DOWN if (o.get("direction") == "down" or w.layout.fmt == "short") else RIGHT
    nodes.arrange(direction, buff=0.7)
    arrows = VGroup(*[Arrow(a.get_edge_center(direction), b.get_edge_center(-direction), buff=0.08, color=color("muted"), stroke_width=4)
                      for a, b in zip(nodes[:-1], nodes[1:])])
    return VGroup(nodes, arrows)


@register("image")
def _image(o, w):
    from pathlib import Path

    p = Path(o["path"])
    if not p.is_absolute() and w.base_dir:
        p = Path(w.base_dir) / p
    img = ImageMobject(str(p)).set_height(o.get("height", 3))
    if "at" in o:
        return img.move_to(w.xy(o["at"]))
    return img.move_to(w.layout.zone(o.get("zone", "stage")).center)

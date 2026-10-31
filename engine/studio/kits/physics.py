"""Physics kit: road, car, race with live scoreboard, light ray, optical media, spring, incline, pulley."""
import numpy as np
from manim import (
    DOWN, LEFT, RIGHT, UP, Angle, Circle, DashedLine, Dot, FadeIn, Line, Polygon, Rectangle, RoundedRectangle, TracedPath,
    UpdateFromAlphaFunc, ValueTracker, VGroup, VMobject, always_redraw, linear,
)

from .. import layout as L
from ..brand import BOLD, T, color, glow_box
from ..objects import c, register
from ..ops import register as register_op


# ---- motion maths ------------------------------------------------------------------
def route_state(pts, speeds, t):
    """Position, heading and finish time after time t on a polyline with per-segment speeds."""
    elapsed, heading = 0.0, 0.0
    for i in range(len(pts) - 1):
        a, b = np.array(pts[i], float), np.array(pts[i + 1], float)
        seg = np.linalg.norm(b - a) / speeds[i]
        heading = np.arctan2(*(b - a)[[1, 0]])
        if t <= elapsed + seg:
            return a + (b - a) * (t - elapsed) / seg, heading, None
        elapsed += seg
    return np.array(pts[-1], float), heading, elapsed


def route_time(pts, speeds):
    return sum(np.linalg.norm(np.array(pts[i + 1], float) - np.array(pts[i], float)) / speeds[i] for i in range(len(pts) - 1))


# ---- objects ---------------------------------------------------------------------------
@register("physics.road")
def road(o, w):
    a, b = w.xy(o["from"]), w.xy(o["to"])
    h = o.get("width", 0.3)
    band = Rectangle(width=np.linalg.norm(b - a), height=h).move_to((a + b) / 2).set_fill("#2A2F3A", 1).set_stroke(width=0)
    band.rotate(np.arctan2(*(b - a)[[1, 0]]))
    n = np.array([0, h / 2, 0])
    edges = VGroup(Line(a + n, b + n), Line(a - n, b - n)).set_stroke("#C9CED8", 1.5, opacity=0.8)
    dashes = DashedLine(a, b, dash_length=0.14, dashed_ratio=0.5).set_stroke("#E9C46A", 1.6, opacity=0.6)
    return VGroup(band, edges, dashes)


class Car(VGroup):
    """Top-down car facing +x; .place(pos, angle) turns and moves it."""

    def __init__(self, col, scale=1.0):
        super().__init__()
        body = RoundedRectangle(corner_radius=0.08, width=0.5, height=0.26).set_fill(col, 1).set_stroke("#FFFFFF", 1, 0.5)
        cabin = RoundedRectangle(corner_radius=0.05, width=0.24, height=0.2).set_fill("#000000", 0.45).set_stroke(width=0).shift(LEFT * 0.03)
        wheels = VGroup(*[Rectangle(width=0.11, height=0.045).set_fill("#111111", 1).set_stroke(width=0).move_to([x, y, 0]) for x in (-0.15, 0.15) for y in (-0.145, 0.145)])
        lights = VGroup(*[Dot([0.24, y, 0], radius=0.025, color="#FFF4B0") for y in (-0.08, 0.08)])
        self.add(wheels, body, cabin, lights)
        self.scale(scale)
        self.angle = 0.0

    def place(self, pos, angle):
        self.rotate(angle - self.angle)
        self.angle = angle
        return self.move_to(pos)


@register("physics.car")
def car(o, w):
    return Car(c(o, "good"), o.get("scale", 1.0)).place(w.xy(o["at"]), np.radians(o.get("heading", 0)))


@register("physics.ray")
def ray(o, w):
    path = VMobject().set_points_as_corners([w.xy(p) for p in o["path"]])
    col = c(o, "accent")
    return VGroup(path.copy().set_stroke(col, 22, 0.15), path.copy().set_stroke(col, 10, 0.3), path.copy().set_stroke("#FFF3C4", 4))


@register("physics.media")
def media(o, w):
    """Two optical media split at world height `boundary`, with labels."""
    st = w.spec.stage
    top = Polygon(w.xy([0, o["boundary"]]), w.xy([st.width, o["boundary"]]), w.xy([st.width, st.height]), w.xy([0, st.height]))
    bot = Polygon(w.xy([0, 0]), w.xy([st.width, 0]), w.xy([st.width, o["boundary"]]), w.xy([0, o["boundary"]]))
    top.set_fill(color(o.get("top_color", "#1B2A35")), 1).set_stroke(width=0)
    bot.set_fill(color(o.get("bottom_color", "#16304A")), 1).set_stroke(width=0)
    g = VGroup(top, bot, Line(w.xy([0, o["boundary"]]), w.xy([st.width, o["boundary"]])).set_stroke(color("muted"), 2))
    if o.get("top_label"):
        g.add(T(o["top_label"], 24, "road").next_to(top.get_corner(UP + RIGHT), DOWN + LEFT, buff=0.15))
    if o.get("bottom_label"):
        g.add(T(o["bottom_label"], 24, "#8FC3F2").next_to(bot.get_corner(DOWN + LEFT), UP + RIGHT, buff=0.2))
    return g


@register("physics.spring")
def spring(o, w):
    a, b = w.xy(o["from"]), w.xy(o["to"])
    d = b - a
    n = np.array([-d[1], d[0], 0]) / max(np.linalg.norm(d), 1e-6)
    coils = o.get("coils", 8)
    pts = [a] + [a + d * (k + 0.5) / (2 * coils) + n * 0.18 * (1 if k % 2 else -1) for k in range(2 * coils)] + [b]
    return VMobject().set_points_as_corners(pts).set_stroke(c(o, "primary"), 3)


@register("physics.incline")
def incline(o, w):
    base = w.xy(o["at"])
    width = w.length(o.get("width", 3))
    th = np.radians(o.get("angle", 30))
    tri = Polygon(base, base + RIGHT * width, base + RIGHT * width + UP * width * np.tan(th))
    tri.set_fill(color("muted"), 0.2).set_stroke(color("muted"), 2)
    ang = Angle(Line(base, base + RIGHT), Line(base, base + np.array([np.cos(th), np.sin(th), 0])), radius=0.5).set_stroke(color("accent"), 3)
    return VGroup(tri, ang)


@register("physics.pulley")
def pulley(o, w):
    ctr = w.xy(o["center"])
    r = w.length(o.get("radius", 0.4))
    wheel = Circle(radius=r).move_to(ctr).set_stroke(c(o, "ink"), 3)
    ropes = VGroup(Line(ctr + LEFT * r, ctr + LEFT * r + DOWN * w.length(o.get("left_drop", 1.2))),
                   Line(ctr + RIGHT * r, ctr + RIGHT * r + DOWN * w.length(o.get("right_drop", 0.8)))).set_stroke(color("muted"), 2)
    return VGroup(wheel, Dot(ctr, radius=0.05), ropes)


# ---- race op ---------------------------------------------------------------------------
def live_number(fn, anchor, size=30, suffix="", scale=lambda: 1.0):
    def build():
        m = T(f"{fn():.2f}{suffix}", size, "ink", BOLD).scale(scale())
        return m.move_to(anchor() + RIGHT * m.width / 2)

    return always_redraw(build)


@register_op("race")
def op_race(scene, o, t):
    """Cars drive each route at its speeds; optional live scoreboard; sound on each arrival."""
    w = scene.world
    routes = []
    for r in o["routes"]:
        pts = [w.xy(p) for p in r["path"]]
        speeds = [s * w.scale for s in r["speeds"]]
        routes.append((color(r.get("color", "good")), r.get("label", ""), pts, speeds, route_time(pts, speeds)))
    clock = ValueTracker(0)
    unit = o.get("unit", " min")
    cars, trails = VGroup(), VGroup()
    for col, _, pts, speeds, _ in routes:
        car_m = Car(col, scale=0.8)

        def upd(m, pts=pts, speeds=speeds):
            p, h, _ = route_state(pts, speeds, clock.get_value())
            m.place(p, h)

        car_m.add_updater(upd)
        upd(car_m)
        cars.add(car_m)
        trails.add(TracedPath(car_m.get_center, stroke_color=col, stroke_width=4, stroke_opacity=0.9))
    board = VGroup()
    chip_w0 = 1.0
    if o.get("board"):
        for col, label, *_rest, finish in routes:
            chip = RoundedRectangle(corner_radius=0.06, width=0.36, height=0.2).set_fill(col, 1).set_stroke(width=0)
            board.add(VGroup(chip, T(label, 26, col).next_to(chip, RIGHT, buff=0.2)))
        board.arrange(DOWN, aligned_edge=LEFT, buff=0.38)
        col_x = max(r.width for r in board) + 0.4
        chip_w0 = board[0][0].width
        for row, (*_, finish) in zip(board, routes):
            # the column offset scales with the board, so numbers stay clear of labels after fitting
            row.add(live_number(lambda f=finish: min(clock.get_value(), f) * o.get("time_scale", 1.0),
                                lambda ch=row[0]: ch.get_left() + RIGHT * col_x * ch.width / chip_w0, 30, unit,
                                lambda ch=row[0]: ch.width / chip_w0))
        L.fit(board, L.Box(scene.layout.panel.x0, scene.layout.panel.y0, scene.layout.panel.x1, scene.layout.panel.y1),
              max_scale=1.8 if scene.layout.fmt == "short" else 1.0)
        if scene.layout.fmt == "short":
            board.move_to(scene.layout.panel.center)
    scene.add(trails, cars)
    scene.play(FadeIn(cars, scale=1.5), *([FadeIn(board, shift=LEFT * 0.3)] if len(board) else []), run_time=0.6)
    scene.sfx("engine", gain=-14)
    total = o.get("seconds", 6.0)
    longest = max(r[-1] for r in routes)
    last = 0.0
    order = sorted(range(len(routes)), key=lambda i: routes[i][-1])
    for rank, i in enumerate(order):
        target = routes[i][-1]
        scene.play(clock.animate(rate_func=linear).set_value(target), run_time=max(0.2, total * (target - last) / longest))
        scene.sfx("win" if rank == 0 else "pop", gain=-6)
        last = target
    for m in [*cars, *trails]:
        m.clear_updaters()
    # freeze each live timer as a static final value
    for row, (_, label, *_r, finish) in zip(board, routes):
        live = row[2]
        live.clear_updaters()
        final = T(f"{finish * o.get('time_scale', 1.0):.2f}{unit}", 30, "ink", BOLD).scale(row[0].width / chip_w0)
        final.move_to(live.get_left() + RIGHT * final.width / 2)
        # swap inside the row only: Scene.remove() on a sub-part would split the board apart
        row.remove(live)
        row.add(final)
    scene.race_results = [(label, finish * o.get("time_scale", 1.0)) for _, label, *_r, finish in routes]
    scene.race_board = board
    if len(board):
        win = glow_box(board[order[0]], "good", buff=0.15)
        # The glow belongs to the board only: fade it in by opacity instead of FadeIn, which would
        # also register it as a separate scene object that outlives the board when the panel scrolls.
        parts = win.family_members_with_points()
        full = [p.get_stroke_opacity() for p in parts]
        for p in parts:
            p.set_stroke(opacity=0)
        board.add(win)
        scene.play(UpdateFromAlphaFunc(win, lambda m, a: [p.set_stroke(opacity=f * a) for p, f in zip(parts, full)]), run_time=0.4)
        scene.panel_items.append(board)
    rid = o.get("id", "race")
    w.mobs[rid] = VGroup(trails, cars)  # hide later with {"op": "hide", "ids": ["race"]}
    scene.on_stage.add(rid)

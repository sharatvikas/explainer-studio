"""Spec ops → Manim animations.

Each op is `fn(scene, o, t) -> list[Animation] | None`, where `o` is the op as a
plain dict and `t` the current narration line (t.duration, t.start, t.left()).
Ops that need several plays (countdown, wait, custom) play them directly and
return None. Kits add ops with @register.
"""
import importlib.util
from types import SimpleNamespace

import numpy as np
from manim import (
    DOWN, ORIGIN, UP, UR, Create, FadeIn, FadeOut, FullScreenRectangle, GrowFromCenter, GrowFromEdge, Indicate, LaggedStart,
    Line, ShowPassingFlash, Transform, VGroup, VMobject, Write, always_redraw, linear, smooth, there_and_back, Dot,
)

from . import layout as L
from .brand import BOLD, H, T, color, glow_box, pill
from .expr import Env, evaluate
from .mtex import M

OPS = {}
RATES = {"smooth": smooth, "linear": linear, "there_and_back": there_and_back}


class OpError(ValueError):
    pass


def register(name):
    def deco(fn):
        OPS[name] = fn
        return fn

    return deco


def mobs(scene, o):
    return [scene.world.get(i) for i in o.get("ids", [o["id"]] if "id" in o else [])]


# ---- visibility ------------------------------------------------------------------
@register("show")
def op_show(scene, o, t):
    out = []
    for i in o["ids"]:
        m = scene.world.get(i)
        scene.on_stage.add(i)
        is_point = scene.world.by_id.get(i, {}).get("type") == "point"
        out.append(GrowFromCenter(m) if is_point and i not in scene.world.dynamic else FadeIn(m))
    return out


@register("hide")
def op_hide(scene, o, t):
    for i in o["ids"]:
        scene.on_stage.discard(i)
    return [FadeOut(m) for m in mobs(scene, o)]


@register("create")
def op_create(scene, o, t):
    scene.on_stage.update(o["ids"])
    return [Create(m) if isinstance(m, VMobject) else FadeIn(m) for m in mobs(scene, o)]


@register("write")
def op_write(scene, o, t):
    scene.on_stage.update(o["ids"])
    return [Write(m) if isinstance(m, VMobject) else FadeIn(m) for m in mobs(scene, o)]


@register("fade")
def op_fade(scene, o, t):
    return [m.animate.set_opacity(o.get("to", 0.3)) for m in mobs(scene, o)]


# ---- emphasis ----------------------------------------------------------------------
@register("highlight")
def op_highlight(scene, o, t):
    return [Indicate(m, color=color(o.get("color", "accent")), scale_factor=o.get("scale", 1.15)) for m in mobs(scene, o)]


@register("flash")
def op_flash(scene, o, t):
    return [ShowPassingFlash(m.copy().set_stroke(color(o.get("color", "accent")), 10), time_width=0.6) for m in mobs(scene, o)]


@register("color")
def op_color(scene, o, t):
    return [m.animate.set_color(color(o.get("to", "accent"))) for m in mobs(scene, o)]


@register("move")
def op_move(scene, o, t):
    w = scene.world
    obj = w.by_id[o["id"]]
    obj.update(o["set"])
    new = w.make(obj)
    return [Transform(w.get(o["id"]), new)]


@register("morph")
def op_morph(scene, o, t):
    return [Transform(scene.world.get(o["id"]), scene.world.get(o["into"]).copy())]


@register("tween")
def op_tween(scene, o, t):
    p = o["param"]
    if p not in scene.world.params:
        raise OpError(f"unknown param '{p}'")
    scene.after_play.append(lambda: scene.settle_traces(p))
    return [scene.world.params[p].animate(rate_func=RATES.get(o.get("rate", "smooth"), smooth)).set_value(o["to"])]


@register("camera")
def op_camera(scene, o, t):
    frame = scene.camera.frame
    if scene.layout.fmt == "short":  # a Short is already framed tightly; zooming would crop the hook
        return []
    if o.get("reset"):
        return [frame.animate.move_to(ORIGIN).set(width=scene.layout.frame_w)]
    focus = o.get("focus", "stage")
    if isinstance(focus, list):
        target = VGroup(*[scene.world.get(i) for i in focus])
        center = target.get_center()
    else:
        center = scene.layout.zone(focus).center if focus != "all" else ORIGIN
    return [frame.animate.move_to(center).set(width=scene.layout.frame_w / o.get("zoom", 1.3))]


# ---- panel content --------------------------------------------------------------------
def place_in_panel(scene, mob, gap=0.4):
    """Stack `mob` under the last panel item; scroll older items up and out when full."""
    box = scene.layout.panel
    L.fit(mob, L.Box(box.x0, box.y0, box.x1, box.y0 + box.h * 0.45), max_scale=2.0 if scene.layout.fmt == "short" else 1.0)
    items = scene.panel_items
    if items:
        mob.next_to(items[-1], DOWN, buff=gap).set_x(box.center[0])
    else:
        mob.move_to([box.center[0], box.y1 - mob.height / 2, 0])
    anims = []
    overflow = box.y0 - mob.get_bottom()[1]
    if overflow > 0:
        shift = UP * overflow
        mob.shift(shift)
        keep = []
        for it in items:
            if it.get_top()[1] + overflow > box.y1 + 0.05:
                anims.append(FadeOut(it, shift=shift))
            else:
                keep.append(it)
                anims.append(it.animate.shift(shift))
        scene.panel_items[:] = keep
    scene.panel_items.append(mob)
    return anims


@register("eq")
def op_eq(scene, o, t):
    eq = M(o["tex"], color=color(o.get("color", "ink")), scale=o.get("size", 1.3) * scene.world.text_scale)
    if o.get("replace") and scene.panel_items:
        old = scene.panel_items[-1]
        eq.move_to(old)
        scene.panel_items[-1] = eq
        return [Transform(old, eq)]
    anims = place_in_panel(scene, eq)
    out = anims + [Write(eq)]
    if o.get("box"):
        box = glow_box(eq, o.get("color", "accent"), buff=0.2)
        scene.after_play.append(lambda: scene.play(Create(box), run_time=0.5))
        scene.panel_items[-1] = VGroup(eq, box)
    return out


@register("panel_clear")
def op_panel_clear(scene, o, t):
    items, scene.panel_items[:] = list(scene.panel_items), []
    return [FadeOut(i) for i in items]


@register("callout")
def op_callout(scene, o, t):
    txt = T(o["text"], o.get("size", 30), o.get("color", "accent"), BOLD)
    panel = scene.layout.panel
    if "near" in o:
        txt.next_to(scene.world.get(o["near"]), UP, buff=0.35)
    elif scene.panel_items:
        txt.next_to(scene.panel_items[-1], DOWN, buff=0.5).set_x(panel.center[0])
        if txt.get_bottom()[1] < panel.y0:  # no room under the panel content: use the top of the stage
            txt.move_to([scene.layout.stage.center[0], scene.layout.stage.y1 + 0.3, 0])
    else:
        txt.move_to(panel.center + UP * panel.h * 0.35)
    box = pill(txt, o.get("color", "accent"))
    g = VGroup(box, txt)
    scene.transients.append(g)
    return [FadeIn(g, shift=UP * 0.2)]


@register("reveal")
def op_reveal(scene, o, t):
    lay = scene.layout
    big_middle = lay.fmt == "short" and lay.full_middle
    zone = lay.title if lay.fmt == "short" and not big_middle else lay.panel
    head = H(L.wrap(o["text"], 14 if big_middle else 18), o.get("size", 56), o.get("color", "accent"))
    target = L.Box(zone.x0, zone.center[1] - 2.2, zone.x1, zone.center[1] + 2.2) if big_middle else zone
    L.fit(head, target, max_scale=2.0 if big_middle else 1.0)
    if lay.fmt != "short" or big_middle:
        head.move_to(zone.center)
    for it in scene.panel_items:
        scene.transients.append(it)
    scene.panel_items[:] = []
    scene.transients.append(head)
    scene.sfx(o.get("sfx", "swell"), gain=-8)
    out = [Write(head)]
    if scene.layout.fmt == "short" and scene.hook is not None and scene.hook in scene.mobjects:
        out.append(FadeOut(scene.hook))
    return out


@register("title_card")
def op_title_card(scene, o, t):
    sp = scene.spec
    title = H(L.wrap(sp.title, 22), 60, "ink")
    sub = T(sp.subtitle, 30, "accent") if sp.subtitle else VGroup()
    g = VGroup(title, sub).arrange(DOWN, buff=0.3)
    L.fit(g, scene.layout.full)
    g.move_to(scene.camera.frame.get_center())
    veil = FullScreenRectangle().set_fill(color("bg"), 0.85).set_stroke(width=0).move_to(scene.camera.frame.get_center())
    scene.sfx("swell", gain=-8)
    scene.play(FadeIn(veil), Write(title), FadeIn(sub, shift=UP * 0.2), run_time=min(1.6, t.duration * 0.6))
    scene.wait(max(0.3, t.left() - 0.5))
    scene.play(FadeOut(VGroup(veil, g), shift=UP * 0.2), run_time=0.5)


# ---- data & sequences -------------------------------------------------------------------
@register("graph")
def op_graph(scene, o, t):
    gid = o.get("id", "graph")
    var, (a, b) = o.get("var", "x"), o.get("range", [0, 1])
    params = scene.world.params

    def f(xv):
        vals = {k: v.get_value() for k, v in params.items()}
        vals[var] = xv
        return evaluate(o["fn"], Env(vals, {}))

    if o.get("on"):
        ax = scene.world.axes[o["on"]]
        extra = VGroup()
        new = []
    else:
        ys = [f(x) for x in np.linspace(a, b, 200)]
        lo, hi = o.get("y_range", [min(ys), max(ys)])
        pad = (hi - lo) * 0.1 or 1
        from .objects import _axes

        ax, labels = _axes({"x": [a, b + (b - a) * 0.08], "y": [lo - pad, hi + pad], "x_label": o.get("x_label", var), "y_label": o.get("y_label", ""),
                            "width": 5.0, "height": 2.5, "label_size": 1.3})
        extra = VGroup(ax, labels)
        place_in_panel(scene, extra)
        new = [Create(ax), FadeIn(labels)]
    col = color(o.get("color", "accent"))
    rec = {"axes": ax, "f": f, "range": (a, b), "var": var, "col": col, "frame": extra}
    scene.graphs[gid] = rec
    if o.get("trace") and var in params:
        tr = params[var]
        rec["curve"] = always_redraw(lambda: ax.plot(f, x_range=[a, max(a + 1e-3, min(b, tr.get_value()))], color=col, stroke_width=4))
        rec["dot"] = always_redraw(lambda: Dot(ax.c2p(tr.get_value(), f(tr.get_value())), radius=0.08, color=col))
        rec["value"] = always_redraw(lambda: T(f"{f(tr.get_value()):.2f}", 24, o.get("color", "accent"), BOLD).next_to(rec["dot"], UR, buff=0.08))
        rec["tracing"] = True
        extra.add(rec["curve"], rec["dot"], rec["value"])  # cleared with the panel
        scene.add(rec["curve"], rec["dot"], rec["value"])
        return new
    rec["curve"] = ax.plot(f, x_range=[a, b], color=col, stroke_width=4)
    extra.add(rec["curve"])
    return new + [Create(rec["curve"])]


@register("chart_grow")
def op_chart_grow(scene, o, t):
    chart = scene.world.get(o["id"])
    scene.on_stage.add(o["id"])
    return [LaggedStart(*[GrowFromEdge(bar, DOWN) for bar in chart], lag_ratio=0.2)]


def _step_parts(scene, oid):
    m = scene.world.get(oid)
    kind = scene.world.by_id[oid]["type"]
    if kind == "timeline":
        return [m[0]], list(m[1:])
    if kind == "flow":
        nodes, arrows = m
        parts = [nodes[0]] + [VGroup(arrows[i - 1], nodes[i]) for i in range(1, len(nodes))]
        return [], parts
    return [], list(m)


@register("step")
def op_step(scene, o, t):
    oid = o["id"]
    base, parts = _step_parts(scene, oid)
    k = scene.step_state.get(oid, 0)
    if k >= len(parts):
        return []
    out = [FadeIn(b) for b in base] if k == 0 else []
    scene.step_state[oid] = k + 1
    scene.on_stage.add(oid)
    return out + [FadeIn(parts[k], shift=UP * 0.2)]


@register("countdown")
def op_countdown(scene, o, t):
    lay = scene.layout
    center = lay.title.center if lay.fmt == "short" and not lay.full_middle else lay.panel.center
    for n in range(int(o.get("from", 3)), 0, -1):
        num = H(str(n), 220 if lay.full_middle else 120, "accent").move_to(center)
        scene.sfx("tick", gain=-6)
        scene.play(FadeIn(num, scale=1.4), run_time=0.25)
        scene.play(FadeOut(num, scale=0.8), run_time=0.35)


@register("wait")
def op_wait(scene, o, t):
    scene.wait(o.get("seconds", 0.5))


@register("sfx")
def op_sfx(scene, o, t):
    scene.sfx(o["name"], gain=o.get("gain", -8))


@register("custom")
def op_custom(scene, o, t):
    if scene.base_dir is None:
        raise OpError("custom op needs the spec's folder (base_dir)")
    path = scene.base_dir / o["file"]
    mod_spec = importlib.util.spec_from_file_location(f"custom_{path.stem}", path)
    mod = importlib.util.module_from_spec(mod_spec)
    mod_spec.loader.exec_module(mod)
    ctx = SimpleNamespace(world=scene.world, layout=scene.layout, brand=scene.brand, M=M, T=T, H=H, color=color, line=t)
    getattr(mod, o["fn"])(scene, ctx)

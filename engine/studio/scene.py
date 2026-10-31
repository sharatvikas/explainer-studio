"""SpecScene: plays a video spec as a long-form video, a Short, or a thumbnail still."""
from itertools import groupby
from pathlib import Path

import numpy as np

from manim import DOWN, LEFT, RIGHT, UP, Circle, FadeIn, FadeOut, Group, ImageMobject, RoundedRectangle, VGroup

from . import kits
from . import layout as L
from .brand import BOLD, HEAVY, H, T, activate, color
from .mtex import M
from .objects import ZONED, World
from .ops import OPS, OpError
from .voice import VoiceScene

__all__ = ["make_scene", "OpError"]

# ops whose ids must already be on screen; in a Short, earlier beats may have been skipped
NEEDS_VISIBLE = {"highlight", "flash", "color", "fade", "move", "morph", "hide"}
# ops that put content in the right-hand panel (the camera must show the whole frame)
PANEL_OPS = {"eq", "graph", "reveal", "title_card", "countdown", "chart_grow"}
SHOWING_OPS = {"show", "create", "write", "step"}
MAX_ZOOM = 1.6


class SpecScene(VoiceScene):
    spec = None
    fmt = "long"
    brand = None
    base_dir: Path | None = None

    def setup(self):
        super().setup()
        activate(self.brand)
        self.camera.background_color = color("bg")
        self.voice_name, self.speech_speed = self.brand.voice, self.brand.speed
        kits.load(self.spec.kits)
        self.layout = L.Layout("long" if self.fmt == "thumb" else self.fmt)
        self.world = World(self.spec, self.layout, self.base_dir)
        self.world.build()
        self.on_stage, self.panel_items, self.transients = set(), [], []
        self.graphs, self.step_state, self.after_play = {}, {}, []
        self.hook = None

    # ---------------------------------------------------------------- running
    def construct(self):
        if self.fmt == "thumb":
            return self.thumbnail()
        if self.fmt == "short":
            self.short_hook()
            for i in self.spec.short.beats:
                self.run_beat(self.spec.beats[i], ensure_visible=True)
            self.short_cta()
            return
        for beat in self.spec.beats:
            self.run_beat(beat)
        self.end_card()

    def run_beat(self, beat, ensure_visible=False):
        if beat.chapter and self.fmt == "long":
            self.chapter(beat.chapter)
        with self.say(beat.say, caption=beat.caption) as t:
            ops = sorted(beat.do, key=lambda op: op.at)
            # callouts/reveals from the previous beat leave as this one starts (clutter-free rule)
            stale, self.transients = self.transients, []
            first = True
            framing = self.auto_frame(beat)
            for at, group in groupby(ops, key=lambda op: op.at):
                group = list(group)
                start = t.start + at * t.duration
                if start - self.now > 0.02:
                    self.wait(start - self.now)
                anims = []
                for op in group:
                    o = {"op": op.op, "at": op.at, **(op.model_extra or {})}
                    if op.op not in OPS:
                        raise OpError(f"unknown op '{op.op}'")
                    if ensure_visible and op.op in NEEDS_VISIBLE:
                        self.reveal_silently(o.get("ids", [o["id"]] if "id" in o else []))
                    if o.get("sfx") and op.op not in ("sfx", "reveal"):
                        self.sfx(o["sfx"], gain=-8)
                    anims += OPS[op.op](self, o, t) or []
                if first:
                    anims += [FadeOut(m) for m in stale] + framing
                    stale, framing, first = [], [], False
                if anims:
                    frac = max((op.for_ for op in group if op.for_), default=None) or max(0.2, (1 - at) * 0.85)
                    self.play(*anims, run_time=max(0.3, frac * t.duration))
                self.flush_after_play()
            if stale or framing:
                self.play(*[FadeOut(m) for m in stale], *framing, run_time=0.6)
        self.on_beat_end(beat)

    def auto_frame(self, beat) -> list:
        """Long-form only: frame the diagram when the panel is empty, show everything otherwise.

        Explicit `camera` ops in the beat take over. Returns the camera animation (or nothing).
        """
        if self.fmt != "long" or any(op.op == "camera" for op in beat.do):
            return []
        ops = [(op.op, op.model_extra or {}) for op in beat.do]
        panel_used = bool(self.panel_items) or any(
            name in PANEL_OPS or (name == "callout" and "near" not in x) or (name == "race" and x.get("board"))
            or (name in SHOWING_OPS and any(self.world.by_id.get(i, {}).get("type") in ZONED and self.world.by_id[i].get("zone", "panel") == "panel"
                                            for i in x.get("ids", [x.get("id")])))
            for name, x in ops)
        frame, full_w = self.camera.frame, self.layout.frame_w
        target_c, target_w = np.array([0.0, 0.0, 0.0]), full_w
        if not panel_used:
            ids = set(self.on_stage) - {"race"}
            for name, x in ops:
                if name in SHOWING_OPS:
                    ids.update(i for i in x.get("ids", [x.get("id")]) if i)
                if name == "hide":
                    ids.difference_update(x.get("ids", []))
            mobs = [self.world.get(i) for i in ids if i in self.world.mobs]
            if mobs:
                g = Group(*mobs)
                w, h = g.width + 1.2, g.height + 1.2
                target_w = min(full_w, max(full_w / MAX_ZOOM, w, h * 16 / 9))
                target_c = g.get_center()
        if abs(frame.width - target_w) < 0.05 and np.linalg.norm(frame.get_center() - target_c) < 0.05:
            return []
        return [frame.animate.move_to(target_c).set(width=target_w)]

    def on_beat_end(self, beat):
        """Hook for `studio check` to inspect the screen after each beat."""

    def flush_after_play(self):
        pending, self.after_play = self.after_play, []
        for fn in pending:
            fn()

    def reveal_silently(self, ids):
        for i in ids:
            if i not in self.on_stage:
                self.add(self.world.get(i))
                self.on_stage.add(i)

    def settle_traces(self, param):
        """After a tween, a traced curve becomes the whole static curve (it must not stay cut off)."""
        for rec in self.graphs.values():
            if rec.get("tracing") and rec["var"] == param:
                self.remove(rec["curve"])
                rec["frame"].remove(rec["curve"])
                a, b = rec["range"]
                rec["curve"] = rec["axes"].plot(rec["f"], x_range=[a, b], color=rec["col"], stroke_width=4)
                rec["frame"].add(rec["curve"])
                self.add(rec["curve"])
                self.bring_to_front(rec["dot"], rec["value"])
                rec["tracing"] = False

    # ----------------------------------------------------------- short pieces
    def short_hook(self):
        lines = self.spec.short.hook if self.spec.short else [self.spec.title]
        hook = VGroup(*[H(s, 96, "ink" if i == 0 else "accent") for i, s in enumerate(lines)]).arrange(DOWN, buff=0.1)
        L.fit(hook, self.layout.title)
        self.hook = hook
        self.add(hook)
        self.play(FadeIn(hook, shift=DOWN * 0.3), run_time=0.5)

    def short_cta(self):
        cta = self.spec.short.cta if self.spec.short else ""
        card = VGroup(T(self.brand.channel_name, 40, "ink", BOLD), T(self.brand.channel_url or "Follow for more", 30, "muted")).arrange(DOWN, buff=0.15)
        L.fit(card, self.layout.panel)
        old = list(self.panel_items) + list(self.transients)  # reveal leftovers too: the CTA isn't a beat
        self.panel_items.clear()
        self.transients.clear()
        if old:  # the closing card replaces whatever was in the panel
            self.play(*[FadeOut(m) for m in old], run_time=0.4)
        if cta:
            with self.say(cta) as t:
                self.play(FadeIn(card, shift=UP * 0.3), run_time=min(1.0, t.duration))
        else:
            self.play(FadeIn(card, shift=UP * 0.3), run_time=0.8)
            self.wait(1.0)

    # --------------------------------------------------------------- end card
    def logo(self, height):
        if self.brand.logo and Path(self.brand.logo).exists():
            return ImageMobject(str(self.brand.logo)).set_height(height)
        initials = "".join(w[0] for w in self.brand.channel_name.split()[:2]).upper()
        disc = Circle(radius=height / 2).set_fill(color("accent"), 1).set_stroke(width=0)
        return VGroup(disc, H(initials, 40, "bg").move_to(disc))

    def end_card(self):
        self.play(*[m.animate.set_opacity(0) for m in self.mobjects], run_time=0.6)
        self.clear()
        self.camera.frame.move_to([0, 0, 0]).set(width=self.layout.frame_w)
        name = T(self.brand.channel_name, 34, "ink", BOLD)
        url = T(self.brand.channel_url, 26, "muted") if self.brand.channel_url else VGroup()
        sub_t = T("SUBSCRIBE", 30, "ink", HEAVY)
        sub_bg = RoundedRectangle(corner_radius=0.15, width=sub_t.width + 0.7, height=sub_t.height + 0.45).set_fill("#E53935", 1).set_stroke(width=0)
        card = Group(self.logo(1.3), VGroup(name, url).arrange(DOWN, aligned_edge=LEFT, buff=0.12), VGroup(sub_bg, sub_t.move_to(sub_bg))).arrange(RIGHT, buff=0.5)
        L.fit(card, self.layout.full)  # long channel names/URLs shrink instead of running off-frame
        self.sfx("pop")
        self.play(FadeIn(card, shift=UP * 0.3), run_time=0.8)
        self.wait(2.5)

    # -------------------------------------------------------------- thumbnail
    def thumbnail(self):
        th = self.spec.thumbnail
        upto = next((i for i, b in enumerate(self.spec.beats) if any(op.op in ("race", "graph", "reveal") for op in b.do)), len(self.spec.beats) - 1)
        shown = []
        for b in self.spec.beats[: upto + 1]:
            for op in b.do:
                extra = op.model_extra or {}
                if op.op in ("show", "create", "write"):
                    shown += [i for i in extra.get("ids", []) if i not in shown]
        self.add(*[self.world.get(i) for i in shown])
        if not th:
            return
        lines = VGroup(*[H(s, 84, "ink" if i == 0 else "accent") for i, s in enumerate(th.lines)]).arrange(DOWN, buff=0.12, aligned_edge=LEFT)
        parts = [lines]
        if th.badge:
            bt = T(th.badge, 36, "bg", HEAVY)
            bg = RoundedRectangle(corner_radius=0.15, width=bt.width + 0.6, height=bt.height + 0.4).set_fill(color("good"), 1).set_stroke(width=0)
            parts.append(VGroup(bg, bt.move_to(bg)))
        if th.formula:
            parts.append(M(th.formula, color=color("accent"), scale=1.7))
        right = VGroup(*parts).arrange(DOWN, buff=0.45, aligned_edge=LEFT)
        L.fit(right, self.layout.panel)
        self.add(right)


def make_scene(spec, fmt: str, brand, base_dir=None) -> type:
    name = "".join(p.capitalize() for p in spec.id.replace("_", "-").split("-") if p) + {"long": "Long", "short": "Short", "thumb": "Thumb"}[fmt]
    return type(name, (SpecScene,), {"spec": spec, "fmt": fmt, "brand": brand, "base_dir": Path(base_dir) if base_dir else None})

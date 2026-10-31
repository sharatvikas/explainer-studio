---
name: spec-authoring
description: Reference for writing Explainer Studio video specs (spec.json) — objects, ops, layout, colours, templates, research. Load when writing or fixing a spec; the spec-writer agent reads it first.
---

# Writing an Explainer Studio spec

A spec is a JSON description of one video. The engine turns it into a 1080p long video,
a 1080×1920 Short and a thumbnail. You never write Manim code (except the rare `custom` op).

## Workflow (one item)

1. Read the item (question/notes) and the plan entry (template, outputs, research level).
2. Research & vet per `research.md` → `work/<id>/research.md` (+ `verify.json` for maths).
3. Read `style-guide.md` and the one template page in `templates/` you're using; read
   `kits/physics.md` only if you use the physics kit.
4. Write `work/<id>/spec.json`. Start from the nearest file in `examples/`.
5. Run `studio check work/<id>/spec.json`. Fix every error and warning (hints included). Max 2 rounds.

## Skeleton

```json
{
  "id": "slug-id", "template": "worked-problem", "title": "Short Punchy Title", "subtitle": "Source · Topic",
  "kits": [], "thumbnail": {"lines": ["TWO OR THREE", "WORDS"], "badge": "SOURCE", "formula": "optional tex"},
  "params": {"x": 1.0},
  "stage": {"width": 10, "height": 6},
  "objects": [ ... ],
  "beats": [ {"chapter": "Hook", "say": "One spoken sentence.", "do": [ ...ops... ]} ],
  "short": {"hook": ["LINE ONE", "LINE TWO"], "beats": [0, 3, 7], "cta": "Spoken closing line."}
}
```

- **World coordinates**: the stage is `width × height` units (default 10 × 6), origin bottom-left.
  It is mapped into the stage zone automatically for both formats.
- **Expressions**: any coordinate may be a string using params and other points:
  `"at": ["A.x + 3.3*x", 5]`. Allowed: numbers, `+ - * / ** %`, `sqrt sin cos tan asin acos atan atan2 exp log abs min max radians degrees pi e`, `P.x`, `P.y`.
  Objects using params redraw every frame, so `tween` animates them.
- **Maths** (`tex`, `label`) is LaTeX-style without a TeX install: `\dfrac \frac \sqrt \vec \hat \sin \cos \eta \theta \ell \circ \rightarrow \left[ \right] \mathrm{km} _ ^`. Use `\dfrac` for display fractions.
- **Colours are semantic**: `primary secondary accent good bad muted ink road field` (or a hex).

## Zones (layout is automatic)

| | Long 16:9 | Short 9:16 |
|---|---|---|
| stage | left 55 %: diagrams | middle |
| panel | right 40 %: equations, lists, cards, graphs, scoreboards | below the stage |
| title | top strip | top (the hook title lives here) |
| captions | — | burned in by post-production |

Zoned objects (`bullet_list card code table axes bar_chart line_chart number_line timeline flow`) are fitted into `"zone"` (`panel` default, or `stage`) unless you give `"at"`.

## Objects

| Type | Fields (besides `id`, `type`) |
|---|---|
| `point` | `at`, `label`, `label_dir` (up/down/left/right/ul/ur/dl/dr), `color`, `label_size` |
| `segment` | `from`, `to` (point id or [x,y]), `color`, `width`, `dashed` |
| `polyline` | `path` (list of ids/points), `color`, `width` |
| `arrow` | `from`, `to`, `color` |
| `vector` | `from`, `to`, `label` |
| `region` | `corners`, `style` (plain/grass/water/glass/hatched), `color` |
| `circle` | `center`, `radius`, `fill` |
| `arc` | `center`, `radius`, `start`, `end` (degrees) |
| `angle` | `vertex`, `from`/`from_dir`, `to`/`to_dir`, `label`, `radius` |
| `dimension` | `from`, `to`, `label`, `side`, `offset` — double arrow with a label |
| `brace` | `from`, `to`, `label`, `plain` (true = words, not maths), `side`, `offset` |
| `label` | `tex`, `at`, `dir`, `offset`, `size` |
| `text` | `text`, `at` or `zone`, `size`, `bold`, `wrap` |
| `bullet_list` | `items` — reveal one by one with `step` |
| `card` | `title`, `body` |
| `code` | `code`, `language`, `line_numbers` |
| `table` | `rows` (first row is the header) |
| `axes` | `x` [min,max], `y`, `x_label`, `y_label` |
| `bar_chart` | `labels`, `values` — grow with `chart_grow` |
| `line_chart` | `x`, `y` lists |
| `number_line` | `range`, `step` |
| `timeline` | `events` [{date, text}] — reveal with `step` |
| `flow` | `nodes` (strings), `direction` — reveal with `step` |
| `image` | `path` (relative to the spec), `height`, `at`/`zone` |

## Ops (each beat's `do` list)

Every op may take `"at"` (0–1, when in the sentence it starts) and `"for"` (fraction of the sentence it lasts) and `"sfx"` (pop, ding, win, whoosh, riser, swell, tick, engine).

| Op | Fields | Effect |
|---|---|---|
| `show` | `ids` | fade/grow in |
| `hide` | `ids` | fade out |
| `create` | `ids` | draw lines/paths |
| `write` | `ids` | write text/maths |
| `fade` | `ids`, `to` | dim to opacity |
| `highlight` | `ids`, `color` | pulse to draw the eye |
| `flash` | `ids`, `color` | light runs along a path |
| `color` | `ids`, `to` | recolour |
| `move` | `id`, `set` {field: value} | rebuild with new fields and morph |
| `morph` | `id`, `into` | turn one object into another |
| `tween` | `param`, `to`, `rate` (smooth/linear/there_and_back) | animate a param — everything using it moves |
| `camera` | `focus` (stage/panel/all/[ids]), `zoom` / `reset: true` | long-form only; ignored in Shorts |
| `eq` | `tex`, `color`, `size`, `box`, `replace` | add a line to the panel (auto-scrolls) |
| `panel_clear` | — | clear the panel |
| `callout` | `text`, `near` (id), `color` | short label in a pill; leaves at the next beat |
| `reveal` | `text` | big headline; leaves at the next beat (in Shorts it replaces the hook) |
| `title_card` | — | full-screen title + subtitle (use once, after the hook) |
| `graph` | `id`, `fn`, `var`, `range`, `trace`, `x_label`, `y_label`, `on` (axes id) | plot in the panel; with `trace` the curve draws as `var` is tweened |
| `chart_grow` | `id` | grow a bar_chart |
| `step` | `id` | reveal the next bullet / timeline event / flow node |
| `countdown` | `from` | 3-2-1 with ticks |
| `wait` | `seconds` | pause |
| `sfx` | `name`, `gain` | sound only |
| `custom` | `file`, `fn` | run `fn(scene, ctx)` from a `.py` next to the spec |
| `race` | see `kits/physics.md` | physics kit |

## Rules that keep videos clean (enforced by `studio check`)

- One idea per beat; `say` ≤ 22 words (check fails above 25).
- ≤ 12 text items on screen (≤ 9 in a Short). `hide` and `panel_clear` old things.
- No text under ~16 px at 1080p; let fitting work by keeping text short.
- Nothing off-screen, no overlapping text. Use `label_dir`, `near`, or a different beat.
- Short: ≤ 45 s, hook ≤ 3 words per line, 4–7 beats, every beat must stand alone.
- Thumbnail: ≤ 3 words per line, one badge, optional formula.

## `custom` (only when ops can't express it)

```python
# work/<id>/custom.py
from manim import Rotate

def spin_wheel(scene, ctx):
    # ctx.world.get(id), ctx.world.xy(ref), ctx.layout, ctx.M(tex), ctx.T(text), ctx.H(text), ctx.color(name), ctx.line.duration
    scene.play(Rotate(ctx.world.get("wheel"), angle=6.28), run_time=ctx.line.duration * 0.8)
```

# Physics kit (`"kits": ["physics"]`)

| Type | Fields |
|---|---|
| `physics.road` | `from`, `to`, `width` — highway with edge lines and a dashed centre line |
| `physics.car` | `at`, `heading` (degrees), `color`, `scale` |
| `physics.ray` | `path` (ids/points) — glowing light ray |
| `physics.media` | `boundary` (world y), `top_label`, `bottom_label`, `top_color`, `bottom_color` — two optical media filling the stage |
| `physics.spring` | `from`, `to`, `coils` |
| `physics.incline` | `at` (bottom-left), `width`, `angle` (degrees) |
| `physics.pulley` | `center`, `radius`, `left_drop`, `right_drop` |

### `race` op
```json
{"op": "race", "board": true, "seconds": 6.5, "unit": " min", "time_scale": 1.0, "id": "race",
 "routes": [{"color": "bad", "label": "Straight across", "path": ["A", "B"], "speeds": [1.65]},
            {"color": "good", "label": "Turn off at C", "path": ["A", "C", "B"], "speeds": [3.3, 1.65]}]}
```
- `speeds` are world units per time unit, one per path segment; the scoreboard shows `distance/speed` in those time units × `time_scale`.
- Cars and trails become object `race` (hide with `{"op": "hide", "ids": ["race"]}`); the scoreboard joins the panel (`panel_clear` removes it).
- Plays sound on each arrival (winner gets `win`).

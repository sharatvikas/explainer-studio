# facts-list ("5 things about X", 1–4 min)
Beats: hook with the most surprising fact (10) → one beat per fact: `card` (title = the fact in ≤ 5 words, body = one sentence) + a supporting visual (object/chart) → `hide` it before the next → recap `bullet_list` stepped.
Short cut: hook + the 3 strongest facts.
Mini example:
```json
{"say": "Fact three: honey never spoils.", "do": [{"op": "panel_clear"}, {"op": "show", "ids": ["card3"]}]}
```

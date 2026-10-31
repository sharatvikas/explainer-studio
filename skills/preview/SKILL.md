---
name: preview
description: Quick low-resolution render of one Explainer Studio item with a contact sheet to review layout before the full render.
argument-hint: <item-id>
---

# Preview one item

`$ARGUMENTS` is an item id with `work/<id>/spec.json`. `STUDIO` = `uv run --project "${CLAUDE_PLUGIN_ROOT}/engine" studio`.

1. `STUDIO check work/<id>/spec.json` — report problems first if any.
2. Render the long video (or the Short if the plan only asks for a Short):
   `STUDIO render work/<id>/spec.json --format long --quality preview --workspace . --channel-name "${user_config.channel_name}" --voice "${user_config.voice}"`
3. `STUDIO sheet work/<id>/long.preview.mp4` (or `short.preview.mp4`) and Read the PNG it prints.
4. Report in ≤ 6 lines: what looks good, anything cluttered, cut off or hard to read, and the fix you'd make to the spec.
   Previews are low resolution on purpose; final videos are always rendered at 1080p by `/explainer-studio:make`.

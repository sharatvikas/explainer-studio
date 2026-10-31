---
name: doctor
description: Diagnose and fix Explainer Studio install problems (engine, fonts, voice model, ffmpeg, rendering).
---

# Explainer Studio doctor

1. Run `uv run --project "${CLAUDE_PLUGIN_ROOT}/engine" studio doctor`.
   If `uv` itself is missing, give the install line from the setup skill and stop.
2. For each FAIL line, explain in one plain sentence what's wrong, show its `fix:`, and offer to run it.
   Common cases:
   - `models` → run `… studio models` (resumes partial downloads).
   - `manim` on macOS → user runs `brew install cairo pkg-config`, then `uv sync --project "${CLAUDE_PLUGIN_ROOT}/engine" --reinstall`.
   - `render` → show the last lines of the error; most often a missing model or an old Python — re-run `uv sync`.
3. Re-run doctor after fixes until every line is OK.

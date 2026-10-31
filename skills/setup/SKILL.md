---
name: setup
description: One-time install for Explainer Studio — Python engine, free voice model, workspace folders and permissions. Run before the first /explainer-studio:make.
---

# Explainer Studio setup

Run each step, check its output, and fix problems before moving on. Commands work in both
PowerShell and Git Bash. `STUDIO` below means exactly:

```
uv run --project "${CLAUDE_PLUGIN_ROOT}/engine" studio
```

1. **uv** — run `uv --version`.
   If it's missing, ask the user to install it themselves (it modifies their PATH), then restart Claude Code:
   - Windows (PowerShell): `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
   - Mac/Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
   Tell them they can type it after `!` in this chat.
2. **Engine** — `uv sync --project "${CLAUDE_PLUGIN_ROOT}/engine"` (first time downloads Python 3.12 + packages, 2–5 min).
   On macOS, if it fails building `pycairo`, ask the user to run `brew install cairo pkg-config`, then retry.
3. **Voice model** — `STUDIO models` (~350 MB, resumable; re-run if interrupted).
4. **Health check** — `STUDIO doctor`. Every line must be OK. For a FAIL, follow its `fix:` line, then re-run.
5. **Workspace** — in the current folder create `input/`, `work/`, `output/`.
   Write `input/EXAMPLE.md`:
   ```markdown
   ## Q1. Which falls first?
   In a vacuum, a bowling ball and a feather are dropped together. Which lands first?
   **Answer:** Both together

   ## Q2. Projectile range
   At what launch angle is a projectile's range greatest on flat ground?
   **Answer:** 45 degrees
   ```
6. **Permissions** — merge (don't overwrite) into `.claude/settings.json` in this folder:
   ```json
   {"permissions": {"allow": ["Bash(uv run --project *)", "Bash(uv sync *)", "Bash(uv --version)", "WebSearch", "WebFetch"]}}
   ```
7. Finish with exactly:
   "Setup complete. Put your notes, questions, PDFs or screenshots in `input/`, then run
   `/explainer-studio:make` (or `/explainer-studio:make input "one quiz Short per question"`)."

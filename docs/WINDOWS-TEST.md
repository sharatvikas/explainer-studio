# Windows smoke test

Run on a clean Windows 10/11 machine (or VM) with Claude Code installed.

1. `/plugin marketplace add <repo or C:\path\to\explainer-studio>` then `/plugin install explainer-studio@explainer-studio-marketplace`; fill the config prompts.
2. Make a folder with a space and a non-English character, e.g. `C:\Users\<you>\Videos\Rāj test`; open Claude Code there.
3. `/explainer-studio:setup`: uv installs, `uv sync` completes, `studio models` downloads, `studio doctor` all OK.
4. Copy `skills/spec-authoring/examples/quiz-short.json`'s question into `input/quiz.md`.
5. `/explainer-studio:make input "one quiz Short"`: `output/<id>/short.mp4` is 1080×1920 with captions; `done.json` exists.
6. Interrupt a second run mid-render (Esc), run `/explainer-studio:make` again: it resumes and the finished item is skipped.
7. Add a screenshot of a handwritten question to `input/`, rerun: a new item appears from the image.
8. `/explainer-studio:doctor`: all OK.

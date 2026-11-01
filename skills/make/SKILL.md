---
name: make
description: Turn everything in a source folder into researched, animated explainer videos (1080p long video, Short, thumbnail, subtitles, description) following a plain-English request.
argument-hint: [folder] ["what you want"]
---

# Make videos from a folder

`$ARGUMENTS` = optional folder (default `input`) and an optional quoted request, e.g.
`input "one 60-second quiz Short per question"`.

`STUDIO` means exactly: `uv run --project "${CLAUDE_PLUGIN_ROOT}/engine" studio`
`BRAND` means exactly: `--workspace . --brand-file work/brand.config.json`

Before the first render, use the **Write tool** (never a shell command, so names with quotes or `$` stay intact)
to write `work/brand.config.json` as JSON with these exact values:
channel_name = ${user_config.channel_name} · channel_url = ${user_config.channel_url} · logo = ${user_config.logo}
· voice = ${user_config.voice}

## Token rules (follow strictly)
- Never Read video/audio files. Read images only to identify items, or a contact sheet when a check fails.
- Text extraction is done by `STUDIO ingest`; read `work/sources.json`, not the original PDFs/docs.
- Spec writing happens in `spec-writer` subagents; keep only their 1-line results here.
- Report progress as one short line per item. No long summaries until the end.

## Steps

1. **Resume** — if `work/plan.json` exists, run `STUDIO status . --json`. Items already `done` are skipped.
   If the user gave a new request or folder, start a new plan instead (keep finished outputs).
   If `uv` is missing or a command fails with an import error, tell the user to run `/explainer-studio:setup`.

2. **Ingest** — `STUDIO ingest <folder> --out work/sources.json`. Read `work/sources.json`.
   For images listed there, Read each one once and write down what it contains (question text, answer, figure).

3. **Plan** — write `work/plan.json`:
   ```json
   {"request": "<user request>", "items": [
     {"id": "irodov-1-17", "title": "Where to Leave the Road", "template": "worked-problem",
      "outputs": ["long", "short", "thumb"], "target_seconds": 240, "research": "vet",
      "source_refs": ["input/questions.md#Q1"], "notes": "answer given: CD = l/sqrt(eta^2-1)"}]}
   ```
   - One item per question for Q&A material; for notes/chapters split by concept (what the request asks).
   - `template`: from the request, else `${user_config.default_template}` (when `auto`, pick: problem → worked-problem,
     concept/notes → concept-explainer, MCQ → quiz, list of facts → facts-list, dated events → timeline, X vs Y → compare).
   - `outputs`: from the request, else `${user_config.default_outputs}` (`long+short+thumb` → `["long","short","thumb"]`).
   - `research`: from the request ("no research" → off, "deep research" → deep), else `${user_config.research}`.
   - ids: lowercase slugs, unique.
   - A `catalogue.csv` (from `/explainer-studio:plan-series`) already gives each row's `id`, `template`, `outputs`
     (`long+short+thumb` style), `answer`, `key_points` and `hook`: use them as given (put `key_points` and `hook`
     in `notes`); the request can still narrow which rows to make ("only the first 3").
   Run `STUDIO plan-check work/plan.json` and fix errors.
   If there are more than 5 items or the request was ambiguous, show a compact table (id · title · template · outputs)
   and ask once whether to proceed. Otherwise proceed.

4. **Specs** — for each item not yet `checked`/`rendered`/`done`, dispatch the `explainer-studio:spec-writer` agent
   (up to 3 at a time) with only:
   - the item's plan entry (JSON),
   - its source text from `work/sources.json` (just that item's text/answer) and any image paths,
   - the workspace path (current folder).
   Each returns one line: `id | verdict | check status`. Items with verdict `unresolved` or a failing check are
   `needs-attention`: don't render them.

5. **Render** — run `STUDIO status . --json`; for every item in state `checked`, render each output listed in its
   `missing` field (outputs that are absent, preview-sized, or older than the spec), in the background
   (at most 2 renders at the same time; each long video takes several minutes):
   `STUDIO render work/<id>/spec.json --format <long|short|thumb> --quality final BRAND`
   If a render fails, read the last 20 lines of `work/<id>/<format>.render.log`, fix the spec if it's a spec problem
   (then re-run `STUDIO check`), retry once, else mark needs-attention.

6. **Package** — when an item's renders are done:
   `STUDIO package work/<id> --out output/<id> --outputs <long,short,thumb> BRAND`
   This writes `output/<id>/` with `long.mp4` (1920×1080), `short.mp4` (1080×1920), `thumbnail.png`,
   `subtitles.srt`, `chapters.txt`, `description.txt`, `done.json`. Copy `work/<id>/research.md` there too.

7. **Report** — write `output/REPORT.md`: a table of item · outputs · durations (from `done.json`) · research verdict
   · notes, plus a "Needs attention" section listing each held-back item with the reason from
   `work/<id>/NEEDS_ATTENTION.md`. Reply to the user in ≤ 10 lines with where the files are.

---
name: plan-series
description: Plan a series of explainer videos on a subject — topics, questions, answers and key points — as an editable catalogue.csv that /explainer-studio:make can turn into videos. Use when the user wants video ideas, a topic list, a syllabus or "what to make next".
argument-hint: "subject, how many videos, audience" [existing-titles.txt]
---

# Plan a video series

`$ARGUMENTS` = a quoted brief (e.g. `"Class 11 kinematics, 10 videos, JEE level"`) and optionally a text file
of titles the channel already has (one per line). `STUDIO` means exactly:
`uv run --project "${CLAUDE_PLUGIN_ROOT}/engine" studio`

## Steps

1. **Brief** — from the arguments, settle: subject, number of videos (default 10), audience/level, and the mix
   (default: about half concepts, half famous problems, plus one or two quizzes). Don't ask unless the subject is missing.
2. **What already exists** — note finished ids in `output/` and titles in the given file; plan around them.
3. **Research** — always run 2–4 WebSearch calls (no more) on the subject's standard syllabus order, the classic
   problems and the misconceptions students hit most. Prefer textbooks, university pages, Khan Academy, HyperPhysics,
   NCERT. Don't copy wording; facts only.
4. **Design the series** — order the items so each builds on the last. For every item:
   - `title`: ≤ 6 words, curiosity first ("Why Rain Doesn't Kill You", not "Terminal Velocity")
   - `kind`: `concept`, `problem`, `quiz`, `facts`, `timeline` or `compare`
   - `question`: the one question the video answers (a full problem statement for problems)
   - `answer`: the correct final answer in words and numbers; for problems give the result, not just the method
   - `key_points`: 2–4 short points the video must land
   - `hook`: the opening line that makes someone stay (a surprise, a wrong intuition, a real-world stake)
   - `difficulty` (`easy`/`medium`/`hard`), `source` (e.g. "Irodov 1.17", "HC Verma Ch 3", "Classic"),
     optional `outputs` (`long+short+thumb`, `short`, …) and `notes`.
   Check each answer yourself before writing it (work it out; use `STUDIO verify` for maths if unsure).
5. **Write** `work/series-<slug>.json`:
   `{"series": "<name>", "audience": "<level>", "items": [ {...}, ... ]}`
   then run `STUDIO catalogue work/series-<slug>.json --out series/<slug> --exclude output <existing-titles file if given>`.
   Fix every error and re-run. For a warning that a topic already exists, replace it with a fresh angle.
6. **Reply** in ≤ 12 lines: a compact table (# · title · kind · difficulty), the path `series/<slug>/catalogue.csv`
   (opens in Excel or Google Sheets — edit, reorder or delete rows freely), and the next step:
   `/explainer-studio:make series/<slug>` for all of them, or e.g.
   `/explainer-studio:make series/<slug> "only the first 3, Shorts only"`.

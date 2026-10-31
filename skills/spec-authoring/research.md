# Research & vetting

Level comes from the plan item (`off | vet | deep`). Do this **before** writing the spec.
Use WebSearch/WebFetch. Record everything in `work/<id>/research.md`.

## vet (default)
1. Solve or explain the item yourself from first principles. Write the key result.
2. Compare with the answer given in the source material (if any).
3. Find 2–3 reputable sources that confirm the result or the facts used:
   - queries: `"<exact concept>" site:.edu`, `<textbook> <problem number> solution`, `<concept> derivation`, `<fact> <authoritative body>`
   - prefer: textbooks, university course pages, standards bodies (NIST, NCERT), Wikipedia only as a pointer to primary sources.
4. For maths/physics write `work/<id>/verify.json` and run `studio verify work/<id>/verify.json`:
   ```json
   [{"kind": "equal", "a": "l/sqrt(eta**2-1)", "b": "1/sqrt(3)", "subs": {"l": 1, "eta": 2}},
    {"kind": "minimum", "f": "x + 2*sqrt((2-x)**2+1)", "var": "x", "range": [0, 2], "expect_at": 1.4226, "tol": 0.001},
    {"kind": "value", "expr": "2 + sqrt(3)", "expect": 3.732, "tol": 0.001},
    {"kind": "symbolic_equal", "a": "...", "b": "...", "assume_positive": true}]
   ```
5. **Gate:** if your derivation, the source answer and the references don't agree, or `studio verify` fails:
   write `work/<id>/NEEDS_ATTENTION.md` (what disagrees, evidence, your best answer) and **stop** — no spec.
   If the source answer has a typo and two references plus verify agree with you, the verdict is `corrected` and you continue with the correct answer (say so in research.md).

## deep (= vet + enrichment)
6. Misconceptions: search `"common misconception" <concept>`, `<concept> students think`. Use 1–2 as the "tempting wrong answers".
7. Hooks: a real-world application or a surprising fact (`<concept> real world example`, `<concept> everyday`).
8. Angle: skim titles/descriptions of the top 3–5 existing videos on the topic; choose a framing they don't use. Never copy their scripts or visuals.

## research.md template
```markdown
# <id> — research
Verdict: verified | corrected | unresolved
Answer check: <your result> vs source <...> — <agree/disagree>
## Sources
- <url> — <title> (accessed YYYY-MM-DD): confirms <what>
## Misconceptions (deep)
## Hooks (deep)
## Angle (deep)
```
Only facts and ideas come from research; all wording and visuals are original.

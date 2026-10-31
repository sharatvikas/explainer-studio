# Style guide — what makes these videos land

1. **Hook in the first 5 seconds.** Open on the surprising thing (a race, a paradox, a question), not a title. Title card comes after the hook.
2. **Every sentence changes the screen.** If a beat's `do` is empty, merge it into a neighbour.
3. **Narration is words, never symbols.** Write `say` as you'd speak it: "sine r equals one over eta", not `$\sin r = 1/\eta$`. Maths goes on screen with `eq`/`label`; `studio check` warns on symbols in `say`.
4. **Short spoken sentences.** 8–22 words. Write how a good teacher talks: "So where should you turn off?" not "We shall now determine the optimal point."
5. **Show before you derive.** Let the viewer *see* the answer (sweep a param, trace a graph, race the options), then prove it.
6. **Colour carries meaning.** Pick one colour per quantity and keep it: the same colour on the diagram, in the equation, and in the graph.
7. **Give payoffs a beat.** Key results get `box: true` plus a `ding`, or a `reveal`. Then pause on them for one sentence.
8. **Tempting wrong answers.** Show the two obvious answers and why they fail before the right one. (Research `deep` finds real misconceptions.)
9. **End with a twist and a question.** A surprising consequence ("there's no d in the answer"), then a viewer challenge for the comments.
10. **Clutter-free.** Clear the panel between ideas; hide labels you no longer need; one focal point at a time.

Do / don't

| Do | Don't |
|---|---|
| "Green wins. Not the shortest path." | "As we can observe, the green vehicle arrives first." |
| 3–5 equations per derivation, each a real step | 10 algebra lines the viewer can't follow by ear |
| A Short that tells one complete idea | A Short that's just the first 45 s of the long video |
| `callout` for a 2–4 word nudge | Paragraphs of on-screen text that duplicate the narration |

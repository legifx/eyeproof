# Benchmark: Claude vs Glimpse as eyes (2026-10-27)

Two sets: **web pages + a video** (below) and **headless 3D renders** (section "3D renders" further down).

> **Caveat.** This is a small benchmark, and the defects were planted by the same author who wrote eyeproof's
> checks. The "tool" numbers are therefore partly by construction: the checks were written knowing what to look
> for. Read the results as a direction (measurements help, a capable image-reading agent beats a cheap vision
> model, video needs measurements), not as a leaderboard. Independent fixtures are welcome.

Setup: 8 pages (6 with 2–3 planted defects each, 2 clean controls) + a 6 s animation with two glitches
(a jump back at 3.0–3.2 s, one full red frame at 4.5 s); 17 defects in total. Every contestant got the same
pictures and the same prompt (`eyeproof.look.REVIEW_PROMPT` + the intent of the page). Two runs each.

- **raw**: pixels only (screenshot; for the video a sheet of 12 evenly spaced frames, Glimpse also got the video).
- **tool**: the full eyeproof pipeline (measured DOM facts in the prompt, a video sheet including the motion-spike frames).
- Claude ran headless (`claude -p --tools Read`, no knowledge of the defects); Glimpse = `elorian/glimpse` on OpenRouter.
- Scoring: regex groups per defect over each issue's `where`+`what` (`truth.json`); every miss and every extra
  issue was read by hand afterwards and the patterns fixed where a correct finding had been missed.

| contestant | mode | found (2 runs) | recall | false alarms on clean pages | unreadable replies | cost per review | avg s |
|---|---|---|---|---|---|---|---|
| glimpse | raw | 24/34 | 71% | 0 | 1 | $0.0136 | 21 |
| glimpse | tool | 30/34 | 88% | 0 | 0 | $0.0110 | 18 |
| opus | raw | 30/34 | 88% | 0 | 0 | $0.0654 | 13 |
| opus | tool | **34/34** | **100%** | 0 | 0 | $0.0668 | 13 |
| sonnet | raw | 30/34 | 88% | 0 | 0 | $0.0296 | 10 |
| sonnet | tool | **34/34** | **100%** | 0 | 0 | $0.0304 | 9 |

Pages only (without the video): Opus and Sonnet 30/30 in both modes, Glimpse 24/30 raw, 28/30 tool.

Claude's cost figures are `claude -p` API-equivalent numbers including Claude Code's own system prompt. Inside a
running session the extra cost of reading a screenshot is only its image tokens, and on the subscription nothing
is billed per call.

## What the numbers hide

- **Glimpse misses fine detail, every time:** the typo "Pasword" (it read "Password") and the round avatar
  stretched into an oval were missed in all 4 Glimpse reviews. Claude caught both in all 8.
- **Glimpse can derail:** once it wrote 98,765 characters of looping reasoning instead of JSON (104 s, $0.07, no
  result). Without a large `max_tokens` (now 24,000) it spends the whole budget thinking and answers nothing.
- **Glimpse on video is not usable as eyes:** with the raw video it found neither glitch in either run and made
  up the same things twice (a "grey track ahead of the progress fill", a "darker pill overlapping the square").
  It also refuses images and video in one request (`mixed modalities … not supported on the vLLM backend`);
  eyeproof now retries with the video alone.
- **The measured layer is what makes video work:** with the motion-spike frames in the sheet, Opus and Sonnet named
  both glitches correctly (solid red frame at 4.5 s; square jumps back to x≈75 at 3.0 s). Glimpse only repeated
  the measured spike times and misread the red frame as a "jump".
- **Extra issues:** all extra issues from Claude that I checked were real (chart without axes, a pre-filled
  password field, dialog copy that contradicts itself, header/body edges not aligned). Glimpse reported fewer
  extras. No contestant raised anything on the two clean pages.
- Measured DOM facts lift everyone: Glimpse 71 → 88 %, Claude 88 → 100 %.

## 3D renders (Blender, headless)

Six scenes rendered with `eyeproof blend` (Eevee, 960x540): one clean, five with one 3D defect each: a table
floating above the grass, the character standing inside the table, the character's head cut off by the frame,
an upside-down tree crown, a missing texture (magenta table). **tool** adds what `eyeproof blend` measures
(missing image file, magenta pixels, objects in view and which frame edge cuts them). Two runs each.

| contestant | mode | found (2 runs) | issues on the clean scene (4 reviews) | unreadable replies | cost per review | avg s |
|---|---|---|---|---|---|---|
| glimpse | raw | 6/10 | 5 | 2 | $0.029 | 44 |
| glimpse | tool | 10/10 | 5 | 0 | $0.022 | 36 |
| opus | raw | 10/10 | 2 | 0 | $0.064 | 16 |
| opus | tool | **10/10** | **0** | 0 | $0.064 | 17 |
| sonnet | raw | 10/10 | 10 | 0 | $0.032 | 14 |
| sonnet | tool | 10/10 | 9 | 0 | $0.031 | 16 |

- Glimpse pixels-only missed the magenta table in both runs, and the floating table and the upside-down tree
  once each. It derailed twice more (≈87k characters of looping text, 94 s, $0.07 each, no answer), so 3 of 60
  Glimpse reviews in total failed this way, all without measurements.
- On the clean scene Glimpse claimed in all 4 reviews that the table "has only three legs". The fourth leg is
  hidden behind another, so this is a perception error, not an extra finding. Sonnet listed style points (no neck,
  mug without handle, flat backdrop) and called the crown's shadow on the wall a stray shape. Opus mentioned only
  the real sliver of sky above the wall, and with the measurements it reported nothing.
- The measured layer again closes Glimpse's gap (6 → 10 of 10). The scene inspector names the missing file and
  the cut edge, so no model has to guess.

## Decision

**Claude Code: look yourself.** Run eyeproof to make and measure the pictures (`shot` / `play` / `blend` /
`frames`), then `Read` them. Claude was the best eye in every category, on pages, video and 3D renders. It needs
no key, and inside a session costs only the image tokens. Opus was the most precise (fewest invented issues).

**Glimpse: only where there is no Claude**, e.g. Hermes or a script/cron job that needs a cheap second look at
pages and renders, always with the measured facts (`review`, or `--model` on `play` / `blend` / `frames`). It costs 1–3 cents per review, roughly half of Sonnet and a third to a sixth of Opus via `claude -p`. It must not be the only check for text accuracy or fine geometry, and never for video.

Raw data: `runs/r1`, `runs/r2`, `runs/r3d-1`, `runs/r3d-2` (not in git; rerun with `bench/run.py`).
